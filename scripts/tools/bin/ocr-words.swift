import Foundation
import Vision
import AppKit
// 使い方: ocr-words a.png b.png ... → 1行＝1語: ファイル名 \t 語 \t x0,y0,x1,y1（画像の画素・左上原点）・英語
let args = Array(CommandLine.arguments.dropFirst())
for path in args {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let W = Double(cg.width), H = Double(cg.height)
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["en-US"]
    req.usesLanguageCorrection = true
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    let name = (path as NSString).lastPathComponent
    for r in req.results ?? [] {
        guard let c = r.topCandidates(1).first else { continue }
        let s = c.string
        s.enumerateSubstrings(in: s.startIndex..<s.endIndex, options: .byWords) { sub, range, _, _ in
            guard let sub = sub, let bb = try? c.boundingBox(for: range) else { return }
            let b = bb.boundingBox
            print("\(name)\t\(sub)\t\(Int(b.minX*W)),\(Int((1-b.maxY)*H)),\(Int(b.maxX*W)),\(Int((1-b.minY)*H))")
        }
    }
}
