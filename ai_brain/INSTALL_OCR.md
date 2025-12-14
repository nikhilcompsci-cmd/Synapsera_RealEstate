# 🖼️ Install Tesseract OCR (For Image-Based PDFs)

Your PDF contains scanned images or screenshots instead of actual text. To process such PDFs, you need to install Tesseract OCR.

---

## ⚠️ Current Issue

```
WARNING - No text extracted with pdfplumber, attempting OCR
WARNING - OCR failed: tesseract.exe is not installed or it's not in your PATH
```

**Translation:** Your PDF is image-based (scanned/screenshots), but OCR software is not installed.

---

## 🚀 Quick Install (Windows)

### Step 1: Download Tesseract OCR
**Download Link:** https://github.com/UB-Mannheim/tesseract/wiki

1. Click on the link above
2. Download: `tesseract-ocr-w64-setup-5.3.3.20231005.exe` (latest version)
3. Run the installer

### Step 2: Install Tesseract
1. **Important:** Install to default location: `C:\Program Files\Tesseract-OCR\`
2. Check: ✅ Add to PATH (during installation)
3. Click "Install"
4. Wait for installation to complete

### Step 3: Verify Installation
Open PowerShell and run:
```powershell
tesseract --version
```

You should see:
```
tesseract 5.3.3
```

### Step 4: Restart Your Server
Stop and restart your FastAPI server for changes to take effect:
```powershell
# Press CTRL+C in the terminal running FastAPI
# Then restart it
py -m uvicorn main:app --reload --port 8000
```

---

## ✅ Test OCR

After installation, try uploading your PDF again:
1. Go to: http://localhost:3000 or open `ui/index.html`
2. Upload your scanned/image-based PDF
3. OCR will automatically process it

Expected log output:
```
INFO - No text extracted with pdfplumber, attempting OCR
INFO - OCR extracted 1234 chars from page 1
INFO - OCR extraction complete: 12345 chars from 10 pages
```

---

## 📋 Supported PDF Types

### ✅ Text-Based PDFs (No OCR needed)
- PDFs created from Word, Excel, PowerPoint
- PDFs with selectable text
- Digitally created documents

### 🖼️ Image-Based PDFs (Requires OCR)
- Scanned documents
- Photos of documents
- Screenshots saved as PDF
- PDFs created from images

---

## 🔍 How to Check Your PDF Type

**Method 1: Try to select text**
- Open PDF in browser or Adobe Reader
- Try to select text with mouse
- ✅ Can select = Text-based (no OCR needed)
- ❌ Cannot select = Image-based (needs OCR)

**Method 2: Check file size**
- Image-based PDFs are usually much larger (5-10 MB+)
- Text-based PDFs are smaller (few hundred KB)

---

## 🎯 Alternative: Convert to Text-Based PDF

Instead of using OCR, you can:

1. **Use Adobe Acrobat Pro:** 
   - Open PDF → Tools → Recognize Text → In This File
   
2. **Use Online Converters:**
   - https://www.adobe.com/acrobat/online/ocr-pdf.html
   - https://www.ilovepdf.com/ocr-pdf

3. **Export from Original Source:**
   - If you have the original document, export as PDF from Word/Excel
   - This produces better quality than scanning

---

## 🐛 Troubleshooting

### Problem: "tesseract is not recognized"
**Solution:** 
1. Make sure you installed to: `C:\Program Files\Tesseract-OCR\`
2. Restart PowerShell/terminal
3. If still not working, manually add to PATH:
   - Windows Search → "Environment Variables"
   - Edit "Path" variable
   - Add: `C:\Program Files\Tesseract-OCR\`
   - Restart terminal

### Problem: OCR extracts gibberish text
**Solution:**
- Scan quality is too low
- Re-scan document at higher DPI (300+ recommended)
- Or use better quality source

### Problem: OCR is too slow
**Solution:**
- OCR processes each page individually
- Large PDFs (50+ pages) will take 2-5 minutes
- Consider using async processing (Celery/Redis)

---

## 💡 Production Alternative: Google Document AI

For production environments, consider using Google Document AI instead of Tesseract:

**Benefits:**
- 95-99% accuracy (vs 70-90% for Tesseract)
- Handles complex layouts, tables, forms
- Much faster processing
- Extracts structured data

**Cost:**
- $1.50 per 1000 pages
- First 1000 pages/month free

**Setup:**
See `GOOGLE_DOCUMENT_AI_SETUP.md` (coming soon)

---

## 📚 Documentation

- Tesseract GitHub: https://github.com/tesseract-ocr/tesseract
- pytesseract Docs: https://pypi.org/project/pytesseract/
- Tesseract Languages: https://github.com/tesseract-ocr/tessdata

---

**Last Updated:** December 14, 2025  
**Status:** OCR Optional - Required only for image-based PDFs
