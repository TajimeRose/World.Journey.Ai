from pathlib import Path

path = Path('templates/index.html')
text = path.read_text(encoding='utf-8')

target = '<span id="imagePreview" class="image-filename" aria-live="polite" data-empty="ยังไม่ได้เลือกไฟล์">ยังไม่ได้เลือกไฟล์</span>'
replacement = '<span id="imagePreview" class="image-filename" aria-live="polite" data-empty="ยังไม่ได้เลือกไฟล์" title="ยังไม่ได้เลือกไฟล์">ยังไม่ได้เลือกไฟล์</span>'
if target not in text:
    raise SystemExit('span not found')
text = text.replace(target, replacement, 1)
path.write_text(text, encoding='utf-8')
