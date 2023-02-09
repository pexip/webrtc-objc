#!/usr/bin/env vpython3

# Copyright 2022-2023 Pexip AS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        '--dsyms',                
        action='store_true',
        default=False,
        help='Include dSYMs.'
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
        args.dsyms,
        args.platforms,
        milestone
    )
    builder.clean()
    builder.build()
    
    # 3. Clean workspace
    workspace.clean()
    
    return 0

if __name__ == '__main__':
  sys.exit(main())
