import Foundation
import Vision
import AppKit
// 使い方: ocr_words <絵の一覧.txt>（1行1枚のパス）→ 1行1語: ファイル名 \t 語 \t x0,y0,x1,y1（画素・左上原点）\t 確かさ \t 行の番号
// 1語ずつの箱＝VNRecognizedText.boundingBox(for:) を空白で割った語ごとに（英語＋日本語）
let list = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ""
let paths = ((try? String(contentsOfFile: list, encoding: .utf8)) ?? "").split(separator: "\n").map(String.init).filter { !$0.isEmpty }
for path in paths {
    autoreleasepool {
        guard let img = NSImage(contentsOfFile: path),
              let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("\((path as NSString).lastPathComponent)\tERR\t\t0\t0"); return }
        let W = Double(cg.width), H = Double(cg.height)
        let req = VNRecognizeTextRequest()
        req.recognitionLevel = .accurate
        req.recognitionLanguages = ["en-US", "ja-JP"]
        req.usesLanguageCorrection = true
        req.minimumTextHeight = 0.015
        try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
        var li = 0
        for r in req.results ?? [] {
            guard let cand = r.topCandidates(1).first else { continue }
            let s = cand.string
            var start = s.startIndex
            while start < s.endIndex {
                while start < s.endIndex && s[start] == " " { start = s.index(after: start) }
                if start >= s.endIndex { break }
                var end = start
                while end < s.endIndex && s[end] != " " { end = s.index(after: end) }
                let word = String(s[start..<end])
                if let bo = try? cand.boundingBox(for: start..<end) {
                    let b = bo.boundingBox
                    print("\((path as NSString).lastPathComponent)\t\(word.replacingOccurrences(of: "\t", with: " "))\t\(Int(b.minX*W)),\(Int((1-b.maxY)*H)),\(Int(b.maxX*W)),\(Int((1-b.minY)*H))\t\(String(format: "%.2f", cand.confidence))\t\(li)")
                }
                start = end
            }
            li += 1
        }
    }
}
