// swift-tools-version:5.3

// Copyright 2022-2023 Pexip AS
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import PackageDescription

let package = Package(
    name: "WebRTC",
    platforms: [
    	.iOS(.v13),
        .macOS(.v10_15)
    ],
    products: [
        .library(
            name: "WebRTC",
            targets: ["WebRTC"]
        ),
    ],
    dependencies: [],
    targets: [
        .binaryTarget(
            name: "WebRTC",
            url: "https://api.github.com/repos/pexip/webrtc-objc/releases/assets/120636105.zip",
            checksum: "2deb321d5d59248a753ad77d8d96e24acf71bff08616cc0622107a1d20bdccd0"
        ),
    ]
)
