#!/usr/bin/env vpython3

import sys
import logging
import argparse
from typing import List

### - SCRIPT ARGUMENTS

def parse_args() -> List:
    # WebRTC is not properly working on MacCatalyst yet.
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
        default=['ios', 'simulator', 'mac'],
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
        default=False,
        help='Include dSYMs. Has no effect when compiled with bitcode.'
    )
    return parser.parse_args()

### - MAIN

def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    args = parse_args()
    milestone = f"{args.milestone}"
    
    # 1. Prepare workspace
    from webrtc_workspace import WebRTCWorkspace
    workspace = WebRTCWorkspace(milestone)
    workspace.prepare()
    
    # 2. Create xcframework
    from webrtc_builder import WebRTCBuilder
    
    builder = WebRTCBuilder(
        workspace.webrtc_path,
        workspace.depot_tools_path,
        workspace.output_path,
        args.bitcode,
        args.dsyms,
        args.platforms,
        milestone
    )
    builder.clean()
    builder.build()
    
    # 4. Clean workspace
    workspace.clean()
    
    return 0

if __name__ == '__main__':
  sys.exit(main())
