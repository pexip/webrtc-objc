#!/usr/bin/env vpython3

import sys
import os
import logging
import shutil
import subprocess
from typing import List
from dataclasses import dataclass

os.environ['PATH'] = '/usr/libexec' + os.pathsep + os.environ['PATH']

### - CONSTANTS

FRAMEWORK_NAME = 'WebRTC.framework'
DSYM_NAME = 'WebRTC.dSYM'
XCFRAMEWORK_NAME = 'WebRTC.xcframework'

### - CLASSES

@dataclass
class Platform:
    environment: str
    deployment_target: str
    architectures: List[str]

    @property
    def gn_target_name(self):
        is_mac = self.environment == 'mac'
        return 'mac_framework_objc' if is_mac else 'framework_objc'

@dataclass
class WebRTCBuilder:
    run_path: str
    depot_tools_path: str
    output_path: str
    bitcode: bool
    dsyms: bool
    platform_names: List[str]
    version_number: str

    @property
    def xcframework_path(self) -> str:
        return os.path.join(self.output_path, XCFRAMEWORK_NAME)
    
    ### - Public

    def build(self):
        platforms = [self._parse_platform(name) for name in self.platform_names]
        platform_paths = []
        target_lib_paths = dict()
    
        # 1. Build libs for all selected platforms
        for platform in platforms:
            platform_path = os.path.join(self.output_path, platform.environment)
            platform_paths.append(platform_path)
            gn_target_name = platform.gn_target_name
            lib_paths = self._build_libs(platform, platform_path)

            if target_lib_paths.get(gn_target_name) is None:
                target_lib_paths[gn_target_name] = []
        
            target_lib_paths[gn_target_name] += lib_paths

        # 2. Create xcframework
        self._create_xcframework(platform_paths)

        # 3. Generate the license file
        self._generate_license(target_lib_paths)
        
        logging.info('Done.')

    def clean(self):
        logging.info(f"Deleting {self.output_path}")
        shutil.rmtree(self.output_path, ignore_errors = True)

    ### - Private

    @property
    def _common_gn_args(self) -> List[str]:
        return [
            'is_component_build=false',
            'rtc_include_tests=false',
            'is_debug=false',
            'rtc_libvpx_build_vp9=false',
            'use_goma=false',
            'rtc_enable_objc_symbol_export=true',
            'enable_stripping=true',
            'enable_dsyms=' + ('true' if self.dsyms else 'false')
        ]

    def _ios_gn_args(
        self, 
        target_cpu: str, 
        target_environment: str, 
        deployment_target: str
    ) -> List[str]:
        return [
            'target_os="ios"',
            f"target_cpu=\"{target_cpu}\"",
            f"target_environment=\"{target_environment}\"",
            'ios_enable_code_signing=false',
            f"ios_deployment_target=\"{deployment_target}\"",
            f"enable_ios_bitcode={('true' if self.bitcode else 'false')}"
        ]

    def _mac_gn_args(self, target_cpu: str, deployment_target: str) -> List[str]:
        return [
            'target_os="mac"',
            f"target_cpu=\"{target_cpu}\"",
            f"mac_deployment_target=\"{deployment_target}\""
        ]

    def _parse_platform(self, name: str) -> Platform:
        if name == 'ios':
            return Platform('device', '12.0', ['arm64'])
        elif name == 'simulator':
            return Platform(name, '12.0', ['arm64', 'x64']) 
        elif name == 'catalyst':
            return Platform(name, '14.0', ['arm64', 'x64'])
        elif name == 'mac':
            return Platform(name, '10.11.0', ['arm64', 'x64'])
        else:
            raise NotImplementedError
            
    def _build_libs(self, platform: str, platform_path: str) -> List[str]:
        lib_paths = []
    
        # 1. Build WebRTC dylibs
        for architecture in platform.architectures:
            lib_path = os.path.join(platform_path, architecture + '_libs')
            lib_paths.append(lib_path)
            self._build_dlyb(platform, architecture, lib_path)            
        
        # 2. Merge dylibs
        logging.info(f"Merging dylibs for {platform.environment}.")
        self._merge_dylibs(platform_path, lib_paths)
        
        # 3. Merge dsyms if needed
        if self.dsyms:
            logging.info(f"Merging dsyms for {platform.environment}.")
            self._merge_dsyms(platform_path, lib_paths)
        
        # 4. Set version number
        self._set_version_number(platform_path)

        return lib_paths

    def _build_dlyb(self, platform: Platform, architecture: str, lib_path: str):
        gn_args = []
        if platform.environment == 'mac':
            gn_args = self._mac_gn_args(
                architecture, 
                platform.deployment_target
            )
        else:
            gn_args = self._ios_gn_args(
                architecture,
                platform.environment,
                platform.deployment_target
            )
        gn_args += self._common_gn_args
        self._build_webrtc(gn_args, platform.gn_target_name, lib_path)

    def _build_webrtc(self, gn_args: List[str], gn_target_name: str, output_dir: str):
        args_string = ' '.join(gn_args)
        
        logging.info(f"Building WebRTC with args: {args_string}")
        self._run([
            sys.executable,
            os.path.join(self.depot_tools_path, 'gn.py'),
            'gen',
            output_dir,
            f"--args={args_string}"
        ])
        
        logging.info(f"Building target: {gn_target_name}")
        self._run([
            os.path.join(self.depot_tools_path, 'ninja'),
            '-C',
            output_dir,
            gn_target_name
        ])

    def _merge_dylibs(self, platform_path: str, lib_paths: List[str]):
        dylib_path = os.path.join(FRAMEWORK_NAME, 'WebRTC')
        shutil.copytree(
            os.path.join(lib_paths[0], FRAMEWORK_NAME),
            os.path.join(platform_path, FRAMEWORK_NAME),
            symlinks=True
        )
        in_dylib_paths = [os.path.join(path, dylib_path) for path in lib_paths]
        out_dylib_path = os.path.join(platform_path, dylib_path)
        if os.path.islink(out_dylib_path):
            out_dylib_path = os.path.join(
                os.path.dirname(out_dylib_path),
                os.readlink(out_dylib_path)
            )
        self._run(['lipo'] + in_dylib_paths + ['-create', '-output', out_dylib_path])

    def _merge_dsyms(self, platform_path: str, lib_paths: List[str]):
        dsym_dir_path = os.path.join(lib_paths[0], DSYM_NAME)
        if os.path.isdir(dsym_dir_path):
            logging.info('Merging dSYMs.')
            shutil.copytree(
                dsym_dir_path,
                os.path.join(platform_path, DSYM_NAME)
            )
            dsym_path = os.path.join(DSYM_NAME, 'Contents', 'Resources', 'DWARF', 'WebRTC')
            in_dsym_paths = [os.path.join(path, dsym_path) for path in lib_paths]
            out_dsym_path = os.path.join(platform_path, dsym_path)
            self._run(['lipo'] + in_dsym_paths + ['-create', '-output', out_dsym_path])

    def _set_version_number(self, platform_path: str):
        resources_dir = os.path.join(platform_path, FRAMEWORK_NAME, 'Resources')
        if not os.path.exists(resources_dir):
            resources_dir = os.path.dirname(resources_dir)
        infoplist_path = os.path.join(resources_dir, 'Info.plist')
        
        logging.info(f"Setting version number: {self.version_number}")
        self._run([
            'PlistBuddy', '-c', 'Set :CFBundleVersion ' + self.version_number,
            infoplist_path
        ])
        self._run([
            'PlistBuddy', '-c', 'Set :CFBundleShortVersionString ' + self.version_number,
            infoplist_path
        ])
        self._run(['plutil', '-convert', 'binary1', infoplist_path])

    def _create_xcframework(self, platform_paths: List[str]):
        logging.info('Creating xcframework.')
        command = ['xcodebuild', '-create-xcframework', '-output', self.xcframework_path]

        for platform_path in platform_paths:
            command += ['-framework', os.path.join(platform_path, FRAMEWORK_NAME)]
            dsym_path = os.path.join(platform_path, DSYM_NAME)
            if os.path.exists(dsym_path):
                command += ['-debug-symbols', dsym_path]

        self._run(command)

    def _generate_license(self, target_lib_paths: dict):
        logging.info('Generating license file.')
        for gn_target_name, lib_paths in target_lib_paths.items():
            self._run([
                sys.executable, 
                os.path.join(self.run_path, 'tools_webrtc', 'libs', 'generate_licenses.py'), 
                '--target', 
                "//sdk:" + gn_target_name, 
                self.xcframework_path
            ] + lib_paths)

    def _run(self, cmd: List[str]):
        logging.debug(f"Running: {' '.join(cmd)}")
        subprocess.check_call(cmd, cwd=self.run_path)
