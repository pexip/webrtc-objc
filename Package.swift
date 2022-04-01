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
            url: "https://github.com/pexip/webrtc-ios-builds/releases/download/webrtc-2021.08.18-cat/WebRTC.xcframework.zip",
            checksum: "6965b0b8660080797647372c5806b425f8dbb97bb5d8fe1cf4cee753a7dc512e"
        ),
    ]
)
