// swift-tools-version:5.3
import PackageDescription

let package = Package(
    name: "WebRTC",
    platforms: [
    	.iOS(.v13),
    ],
    products: [
        .library(name: "WebRTC", targets: ["WebRTC"]),
    ],
    dependencies: [],
    targets: [
        .binaryTarget(
            name: "WebRTC",
            url: "https://api.github.com/repos/pexip/webrtc-ios-builds/releases/assets/61456711",
            checksum: "48bfa3b63dc5cb829570108e59cbd069d7d8446f4da0e1ea46a8e32cd547d71b"
        ),
    ]
)
