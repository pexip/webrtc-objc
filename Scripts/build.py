#!/usr/bin/env vpython3

import os
import sys
import logging
import subprocess
import argparse
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

### - SCRIPT ARGUMENTS

def parse_args() -> List:
    platform_names = ['ios', 'simulator', 'catalyst', 'mac']
    parser = argparse.ArgumentParser(description='Create WebRTC xcframework')
    parser.add_argument(
        '--milestone',
        type=str,
        default='stable',
        help='WebRTC milestone. Defaults to latest stable milestone.'
    )
    parser.add_argument(
        '--platforms',                
        nargs='+',
        default=platform_names,
        choices=platform_names,
        help='Platforms to build. Defaults to %(default)s.'
    )
    parser.add_argument(
        '--bitcode',                
        action='store_true',
        default=False,
        help='Compile with bitcode.'
    )
    parser.add_argument(
        '--dsyms',                
        action='store_true',
        default=True,
        help='Include dSYMs. Has no effect when compiled with bitcode.'
    )
    return parser.parse_args()

### - FUNCTIONS

def download_depot_tools():
    if not os.path.isdir(DEPOT_TOOLS_PATH):
        logging.info('Cloning depot_tools...')
        run([
            'git', 
            'clone', 
            'https://chromium.googlesource.com/chromium/tools/depot_tools.git'
        ])
    else:
        logging.info('Updating depot_tools...')
        run(['git', 'pull', 'origin', 'main'], DEPOT_TOOLS_PATH)
    os.environ['PATH'] = DEPOT_TOOLS_PATH + os.pathsep + os.environ['PATH']

def fetch_stable_webrtc_milestone() -> str:
    logging.info('Fetching latest stable WebRTC milestone...')
    releases = requests.get(
        'https://chromiumdash.appspot.com/fetch_milestones?only_branched=true'
    ).json()
    release = next(
        filter(lambda m: m['schedule_phase'] == 'stable', releases), 
        releases[0]
    )
    return release['milestone']

def fetch_webrtc_branch_name(milestone: str) -> str:
    logging.info(f"Fetching WebRTC branch name for m{milestone}...")
    releases = requests.get(
        f"https://chromiumdash.appspot.com/fetch_milestones?mstone={milestone}"
    ).json()
    return f"branch-heads/{releases[0]['webrtc_branch']}"

def download_webrtc(branch: str):
    logging.info(f"Fetching WebRTC branch name {branch}...")
    if not os.path.isdir(WEBRTC_PATH):
        run(['fetch', '--nohooks', 'webrtc_ios'])
    run(['git', 'fetch', '--all'], WEBRTC_PATH)
    run(['git', 'checkout', branch], WEBRTC_PATH)
    run(['git', 'pull', 'origin', branch], WEBRTC_PATH)
    # Antivirus software could detect one of the files 
    # in "src/third_party" folder as a virus and delete it. 
    # Commit the change because otherwise "gclient sync" would fail.
    run(['git', 'add', '.'], THIRD_PARTY_PATH)
    run(['git', 'commit', '-m', 'Temp local changes'], THIRD_PARTY_PATH)

def sync_gclient():
    logging.info('Syncing gclient')
    run(['gclient', 'sync', '--with_branch_heads', '--with_tags'])
    
def apply_patches():
    # Merge conflicts here indicate it's time to update the patch.
    for patch in WEBRTC_PATCHES:
        run(['git', 'am', '-3', patch], WEBRTC_PATH)
    for patch in BUILD_PATCHES:
        run(['git', 'am', '-3', patch], WEBRTC_BUILD_PATH)

def clean():
    git_reset(DEPOT_TOOLS_PATH)
    git_reset(WEBRTC_PATH)
    git_reset(WEBRTC_BUILD_PATH)
    git_reset(THIRD_PARTY_PATH)

def git_reset(cwd: str):
    run(['git', 'reset', '--hard', 'origin'], cwd)

def run(cmd: List[str], cwd: str = CWD_PATH):
    logging.debug(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd)

### - MAIN

def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    args = parse_args()
    
    # 1. Download depot_tools
    download_depot_tools()

    # 2. Fetch WebRTC branch name
    milestone = args.milestone
    if milestone == 'stable':
        milestone = fetch_stable_webrtc_milestone()
    if milestone == 'main':
        branch = 'main'
    else:
        branch = fetch_webrtc_branch_name(milestone)

    # 2. Download and sync WebRTC
    download_webrtc(branch)
    sync_gclient()
    apply_patches()

    # 3. Create xcframework
    from create_xcframework import WebRTCBuilder
    
    sys.path.append(WEBRTC_BUILD_PATH)
    import find_depot_tools

    builder = WebRTCBuilder(
        WEBRTC_PATH,
        find_depot_tools.DEPOT_TOOLS_PATH,
        OUTPUT_PATH,
        args.bitcode,
        args.dsyms,
        args.platforms,
        f"{milestone}"
    )
    builder.clean()
    builder.build()
    
    # 4. Revert all local Git changes
    clean()
    
    return 0

if __name__ == '__main__':
  sys.exit(main())
