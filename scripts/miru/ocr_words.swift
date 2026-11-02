import Foundation
import Vision
import AppKit
// 使い方: ocr_words <絵の一覧.txt>（1行1枚のパス）→ 1行1語: ファイル名 \t 語 \t x0,y0,x1,y1（画素・左上原点）\t 確かさ \t 行の番号
// 1語ずつの箱＝VNRecognizedText.boundingBox(for:) を空白で割った語ごとに
// 🔒11/2 手本S（日本語の手本）：Vision は1番目の言語を主にして読む＝英語を先にすると日本語が「L365H」になる（初見 字 0%）
//   → 日本語を先にした読みと英語を先にした読みを両方やり、日本語の字（かな・カナ・漢字・全角）を含む行は日本語の読みを採り、
//     その行と重なる（IoU>0.5）英語の読みは捨てる。英語だけの手本は今までどおり（日本語の読みに日本語の字が出ん限り変わらん）
let list = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ""
let paths = ((try? String(contentsOfFile: list, encoding: .utf8)) ?? "").split(separator: "\n").map(String.init).filter { !$0.isEmpty }

struct Line { var s: String; var cand: VNRecognizedText; var box: CGRect }

func isJa(_ ch: Character) -> Bool {
    // かな・カナ・漢字・半角カナだけ（全角の括弧「（）」や「・」は英語の手本でも Vision が出す＝数えん。手本R の式が「=B（D+P+P+P'）」に化けた）
    guard let u = ch.unicodeScalars.first?.value else { return false }
    return (0x3041...0x3096).contains(u) || (0x30A1...0x30FA).contains(u) || u == 0x30FC || (0x3400...0x9FFF).contains(u) || (0xFF66...0xFF9F).contains(u)
}
func iou(_ a: CGRect, _ b: CGRect) -> Double {
    let i = a.intersection(b); if i.isNull || i.isEmpty { return 0 }
    let ia = Double(i.width * i.height); return ia / (Double(a.width * a.height + b.width * b.height) - ia + 1e-9)
}
func recognize(_ cg: CGImage, _ langs: [String]) -> [Line] {
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = langs
    req.usesLanguageCorrection = true
    req.minimumTextHeight = 0.015
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    var out: [Line] = []
    for r in req.results ?? [] {
        guard let cand = r.topCandidates(1).first else { continue }
        out.append(Line(s: cand.string, cand: cand, box: r.boundingBox))
    }
    return out
}
// 🔒11/2（2回目）：英語の手本でも日本語先の読みは「TESL方」「ルt」」のような日本語っぽい行を出す（手本R 540行・手本J 397・r2 49）＝r2 の字1語・カット3本が消えた
//   → 動画全体で先に「日本語の手本か」を決める：日本語の行の数が英語先の行の数の 2割以上なら日本語の手本（手本S＝6890 対 約2000）。英語の手本（手本R 540 対 57256＝1%）は英語先の読みだけ＝前と同じ
struct Frame { var path: String; var W: Double; var H: Double; var en: [Line]; var ja: [Line] }
var frames: [Frame] = []; var nEn = 0, nJa = 0
for path in paths {
    autoreleasepool {
        guard let img = NSImage(contentsOfFile: path),
              let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { frames.append(Frame(path: path, W: 0, H: 0, en: [], ja: [])); return }
        let en = recognize(cg, ["en-US", "ja-JP"])
        let ja = recognize(cg, ["ja-JP", "en-US"]).filter { l in l.s.contains(where: isJa) }
        nEn += en.count; nJa += ja.count
        frames.append(Frame(path: path, W: Double(cg.width), H: Double(cg.height), en: en, ja: ja))
    }
}
let jaMode = Double(nJa) >= 0.2 * Double(max(1, nEn))
FileHandle.standardError.write("日本語の手本か: \(jaMode)（日本語の行 \(nJa)・英語先の行 \(nEn)）\n".data(using: .utf8)!)
for fr in frames {
    autoreleasepool {
        let path = fr.path; let W = fr.W, H = fr.H
        if W == 0 { print("\((path as NSString).lastPathComponent)\tERR\t\t0\t0"); return }
        var lines: [Line] = jaMode ? fr.ja : []
        for l in fr.en where !lines.contains(where: { iou($0.box, l.box) > 0.5 }) { lines.append(l) }   // 並びは Vision のまま（英語の手本は前と1字も変わらん）
        var li = 0
        for l in lines {
            let s = l.s; let cand = l.cand
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
