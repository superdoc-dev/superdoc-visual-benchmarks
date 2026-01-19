use application "System Events"

--
-- log debug message (uncomment "log" command to enable)
--

global enableDebug

to debug(msg)
  if enableDebug then
    log msg
  end
end debug

--
-- join a list of text items with a specified delimiter
--

to join(someList, delimiter)
  local oldDelimiter, joinedString

  set oldDelimiter to AppleScript's text item delimiters
  set AppleScript's text item delimiters to delimiter

  set joinedString to someList as string

  set AppleScript's text item delimiters to oldDelimiter
  return joinedString
end join

--
-- Get the currently displayed alert modal, or null if none is present
--

to getModal()
  local foundWindows

  tell application "System Events"
    set frontmost of process "Microsoft Word" to true

    set foundWindows to every window of application process "Microsoft Word" whose subrole is "AXDialog" and description is "alert"
    my debug("foundWindows returned windows: " & (length of foundWindows))
    if length of foundWindows > 0 then
      return item 1 of foundWindows
    end if
    return null
  end tell
end getModal

--
-- Get static text within the specified modal window
--

to getModalText(modalWindow)
  return join(value of every static text of modalWindow, "\n")
end getModalText

--
-- Dismiss each modal dialog, if any, in succession
--

to dismissModals()
  local currentModal, staticText, lastMessage

  set lastMessage to null
  set currentModal to getModal()
  repeat until currentModal is null
    -- Get the text of the modal
    set staticText to getModalText(currentModal)
    set lastMessage to staticText

    my debug("Got modal text: " & staticText)

    if staticText contains "Do you want to recover the contents of this document?" then
      click button "No" of currentModal
    else if staticText contains "Word experienced an error trying to open the file." then
      click button "OK" of currentModal
    else
      error "Don't know how to handle modal: " & staticText
    end if

    set currentModal to getModal()
  end repeat

  return lastMessage
end dismissModals


--
-- usage
--
to usage()
  error "Usage: export_word_pdf.applescript [--debug] <docx_path> <pdf_path>"
end

--
-- Open a file in Microsoft Word, signaling an error if it fails'
--
to openFile(docFile)
  local activeDocumentFile

  tell application "Microsoft Word"
    set activeDocumentFile to ref to full name of active document
    try
      with timeout of 3 seconds
        my debug("trying to open docFile " & docFile)
        open docFile
      end timeout
    on error errStr number errorNumber
      -- Dismiss any open modals
      my debug("caught error " & errStr & " errorNumber=" & errorNumber)
      set modalErrorMessage to my dismissModals()

      -- Maybe file was already open, in which case "open" command times out but it selects it as the active document
      my debug("activeDocumentFile is " & activeDocumentFile)
      my debug("docFile is " & docFile)
      if activeDocumentFile as text is docFile as text then
        my debug("successfully opened file despite timeout")
        return
      end if

      if modalErrorMessage is null then
        error "Error opening document, no modals found: " & errStr & ", errorNumber: " & errorNumber
      else
        error "Error opening document: " & modalErrorMessage
      end if
    end try

    if activeDocumentFile as text is not docFile as text then
      error "Expected active document to be " & docFile & ", got " & activeDocumentFile
    end if
  end tell
end openFile


--
-- main
--

on run argv
  local docxPath, pdfPath, docFile, pdfFile

  if count of argv is 2 then
    set enableDebug to false
    set docxPath to item 1 of argv
    set pdfPath to item 2 of argv
  else if count of argv is 3 and item 1 of argv is "--debug" then
    set enableDebug to true
    set docxPath to item 2 of argv
    set pdfPath to item 3 of argv
  else
    usage()
  end if

  set docFile to (POSIX file docxPath) as alias
  set pdfFile to (POSIX file pdfPath)

  -- Ensure that Word is in a sane state: dismiss any existing modals
  tell application "Microsoft Word" to activate
  my debug("dismissing any pre-existing modals...")
  dismissModals()
  my debug("done!")

  openFile(docFile)

  tell application "Microsoft Word"
    -- Not sure if these *actually* have an impact, but just in case...
    set display alerts to alerts none
    set animations to false
  end

  tell application "Microsoft Word"
    -- Sanity check: ensure that active document does not have any unsaved changes
    if active document is not saved then
      error "Document has unsaved changes, aborting"
    end if

    try
      -- Avoid hanging forever if Word doesn't respond
      with timeout of 10 seconds
        my debug("saving document as PDF: " & pdfFile)
        save as active document file name pdfFile file format format PDF
        close active document saving no
        my debug("done!")
      end timeout
    on error errStr number errorNumber
      my debug("caught error " & errStr & " errorNumber=" & errorNumber)
      error "Error saving PDF: " & errStr & ", errorNumber: " & errorNumber
    end try
  end tell
end run
