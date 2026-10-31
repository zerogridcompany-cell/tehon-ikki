import Foundation
import Vision
import AppKit
// 使い方: ocr-lines a.png b.png ... → 1行＝1つの文字の行: ファイル名 \t 文字 \t x0,y0,x1,y1（画像の画素・左上原点）。日本語＋英語
let args = Array(CommandLine.arguments.dropFirst())
for path in args {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("\(path)\tERR\t"); continue }
    let W = Double(cg.width), H = Double(cg.height)
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["en-US"]
    req.usesLanguageCorrection = true
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    for r in req.results ?? [] {
        guard let s = r.topCandidates(1).first?.string else { continue }
        let b = r.boundingBox
        print("\((path as NSString).lastPathComponent)\t\(s.replacingOccurrences(of: "\t", with: " "))\t\(Int(b.minX*W)),\(Int((1-b.maxY)*H)),\(Int(b.maxX*W)),\(Int((1-b.minY)*H))")
    }
}
