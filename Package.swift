// swift-tools-version:5.3
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
            url: "https://api.github.com/repos/pexip/webrtc-ios-builds/releases/assets/77662896.zip",
            checksum: "f8c568fb7dfc983d9024ed091db5fc92b5e4be1416e29de195b327f9100389c5"
        ),
    ]
)
