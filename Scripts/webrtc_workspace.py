#!/usr/bin/env vpython3

import os
import sys
import logging
import subprocess
import requests
from typing import List

### - CONSTANTS

CWD_PATH = os.getcwd()
DEPOT_TOOLS_PATH = os.path.join(CWD_PATH, 'depot_tools')
WEBRTC_PATH = os.path.join(CWD_PATH, 'src')
WEBRTC_BUILD_PATH = os.path.join(WEBRTC_PATH, 'build')
THIRD_PARTY_PATH = os.path.join(WEBRTC_PATH, 'third_party')
OUTPUT_PATH = os.path.join(CWD_PATH, 'out')
PATCHES_PATH = os.path.join(CWD_PATH, 'patches')
WEBRTC_PATCHES = [
    os.path.join(PATCHES_PATH, 'catalyst-fixes.patch')
]
BUILD_PATCHES = [
    os.path.join(PATCHES_PATH, 'bitcode-fixes.patch')
]

sys.path.append(WEBRTC_BUILD_PATH)
import find_depot_tools

class WebRTCWorkspace:
    milestone: str
    branch: str

    def __init__(self, milestone):  
        self.milestone = milestone
        self._set_branch() 

    @property
    def version_number(self) -> str:
        return f"{self.milestone}.0.{self.branch}"

    @property
    def depot_tools_path(self) -> str:
        return find_depot_tools.DEPOT_TOOLS_PATH

    @property
    def webrtc_path(self) -> str:
        return WEBRTC_PATH

    @property
    def output_path(self) -> str:
        return OUTPUT_PATH

    @property
    def commit(self) -> str:
        return _run(['git', 'rev-parse', 'HEAD'], WEBRTC_PATH)

    def prepare(self):
        logging.basicConfig()
        logging.getLogger().setLevel(logging.INFO)
        self._download_depot_tools()
        self._download_webrtc()
        self._sync_gclient()
        self._apply_patches()

    def clean(self):
        self._git_reset(DEPOT_TOOLS_PATH)
        self._git_reset(WEBRTC_PATH)
        self._git_reset(WEBRTC_BUILD_PATH)
        self._git_reset(THIRD_PARTY_PATH)

    def _set_branch(self):
        if self.milestone == 'stable':
            self.milestone = self._fetch_stable_webrtc_milestone()
        self.branch = self._fetch_webrtc_branch_name(self.milestone)

    def _fetch_stable_webrtc_milestone(self) -> str:
        logging.info('Fetching latest stable WebRTC milestone...')
        releases = requests.get(
            'https://chromiumdash.appspot.com/fetch_milestones?only_branched=true'
        ).json()
        release = next(
            filter(lambda m: m['schedule_phase'] == 'stable', releases), 
            releases[0]
        )
        return release['milestone']

    def _fetch_webrtc_branch_name(self, milestone: str) -> str:
        logging.info(f"Fetching WebRTC branch name for m{milestone}...")
        releases = requests.get(
            f"https://chromiumdash.appspot.com/fetch_milestones?mstone={milestone}"
        ).json()
        return f"branch-heads/{releases[0]['webrtc_branch']}"

    def _download_depot_tools(self):
        if not os.path.isdir(DEPOT_TOOLS_PATH):
            logging.info('Cloning depot_tools...')
            _run([
                'git', 
                'clone', 
                'https://chromium.googlesource.com/chromium/tools/depot_tools.git'
            ])
        else:
            logging.info('Updating depot_tools...')
            _run(['git', 'pull', 'origin', 'main'], DEPOT_TOOLS_PATH)
        os.environ['PATH'] = DEPOT_TOOLS_PATH + os.pathsep + os.environ['PATH']

    def _download_webrtc(self):
        logging.info(f"Fetching WebRTC branch name {self.branch}...")
        if not os.path.isdir(WEBRTC_PATH):
            _run(['fetch', '--nohooks', 'webrtc_ios'])
        _run(['git', 'fetch', '--all'], WEBRTC_PATH)
        _run(['git', 'checkout', self.branch], WEBRTC_PATH)
        _run(['git', 'pull', 'origin', self.branch], WEBRTC_PATH)
        # Antivirus software could detect one of the files 
        # in "src/third_party" folder as a virus and delete it. 
        # Commit the change because otherwise "gclient sync" would fail.
        _run(['git', 'add', '.'], THIRD_PARTY_PATH)
        if os.system('echo "$( git status --porcelain | wc -l )"') == 1:
            _run(['git', 'commit', '-m', 'Temp local changes'], THIRD_PARTY_PATH)

    def _sync_gclient(self):
        logging.info('Syncing gclient')
        _run(['gclient', 'sync', '--with_branch_heads', '--with_tags'])
        
    def _apply_patches(self):
        # Merge conflicts here indicate it's time to update the patch.
        for patch in WEBRTC_PATCHES:
            _run(['git', 'am', '-3', patch], WEBRTC_PATH)
        for patch in BUILD_PATCHES:
            _run(['git', 'am', '-3', patch], WEBRTC_BUILD_PATH)

    def _git_reset(cwd: str):
        _run(['git', 'reset', '--hard', 'origin'], cwd)

### - FUNCTIONS

def _run(cmd: List[str], cwd: str = CWD_PATH):
    logging.debug(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd)
