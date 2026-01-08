on run argv
  if (count of argv) is less than 2 then
    error "Usage: export_word_pdf.applescript <docx_path> <pdf_path>"
  end if

  set docxPath to item 1 of argv
  set pdfPath to item 2 of argv

  set docFile to (POSIX file docxPath) as alias
  set pdfFile to (POSIX file pdfPath)

  tell application "Microsoft Word"
    with timeout of 600 seconds
      open docFile
      save as active document file name pdfFile file format format PDF
      close active document saving no
    end timeout
  end tell
end run
