Attribute VB_Name = "MomentumPRO"
'==============================================================================
'  MOMENTUM MIND STORE - INVENTORY MANAGER PRO
'  DESKTOP PRO EDITION MACROS
'
'  The .xlsx you already have is fully working and needs none of this. Import
'  this module only if you want the true ONE-CLICK buttons on Windows or Mac
'  desktop Excel:
'
'      NewSale              one tap: opens the till, stamps today, starts a new
'                           invoice, and drops the cursor in the scan box
'      AddLine              one tap: next line on the SAME invoice
'      GenerateInvoice      one tap: exports the invoice to PDF, then offers to
'                           send it on WhatsApp or attach it to an email
'      SendWhatsApp         opens WhatsApp with the whole invoice pre-typed
'      SendEmailWithPDF     opens an Outlook draft with the PDF attached
'
'  MACROS DO NOT RUN on Excel for iOS, Android or the web. Keep the plain .xlsx
'  as your phone edition and use this .xlsm on the desktop.
'
'  ---------------------------------------------------------------------------
'  HOW TO INSTALL (6 steps, about two minutes)
'  ---------------------------------------------------------------------------
'   1. Open the .xlsx, then File > Save As and choose
'      "Excel Macro-Enabled Workbook (*.xlsm)".
'   2. Press ALT+F11 (Windows) or Tools > Macro > Visual Basic Editor (Mac).
'   3. File > Import File... and choose this VBA_PRO_EDITION.bas
'   4. Close the editor. Back in Excel, go to the Invoice Generator sheet.
'   5. Right-click the "SAVE AS PDF" cell > Assign Macro > GenerateInvoice.
'      Do the same on the Dashboard "START A NEW SALE" cell > NewSale.
'      (Or Insert > Shapes to draw real buttons and assign the macros to those.)
'   6. Save. Excel will warn about macros on first open - click Enable Content.
'==============================================================================
Option Explicit

Private Const SH_SELL   As String = "Log Sale"
Private Const SH_INV    As String = "Invoice Generator"
Private Const SH_SET    As String = "Settings"
Private Const FIRST_ROW As Long = 9      ' first data row on Log Sale
Private Const COL_NEW   As Long = 1      ' A  New-sale tick
Private Const COL_DATE  As Long = 2      ' B  Date
Private Const COL_SCAN  As Long = 4      ' D  SKU / Scan

'------------------------------------------------------------------ helpers --
Private Function NextFreeRow() As Long
    Dim ws As Worksheet, r As Long
    Set ws = ThisWorkbook.Worksheets(SH_SELL)
    r = FIRST_ROW
    Do While Len(Trim$(CStr(ws.Cells(r, COL_SCAN).Value))) > 0
        r = r + 1
        If r > 100000 Then Exit Do
    Loop
    NextFreeRow = r
End Function

Private Function DigitsOnly(ByVal s As String) As String
    Dim i As Long, ch As String, out As String
    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        If ch >= "0" And ch <= "9" Then out = out & ch
    Next i
    DigitsOnly = out
End Function

' Excel builds the share text in hidden cell I7 already URL-encoded.
Private Function InvoiceText() As String
    InvoiceText = CStr(ThisWorkbook.Worksheets(SH_INV).Range("I7").Value)
End Function

Private Function CurrentInvoiceNo() As String
    CurrentInvoiceNo = Trim$(CStr(ThisWorkbook.Worksheets(SH_INV).Range("B7").Value))
End Function

'--------------------------------------------------------------- ONE TAP: SELL
Public Sub NewSale()
    Dim ws As Worksheet, r As Long
    Set ws = ThisWorkbook.Worksheets(SH_SELL)
    ws.Activate
    r = NextFreeRow()
    ws.Cells(r, COL_NEW).Value = "x"
    ws.Cells(r, COL_DATE).Value = Date
    Application.Goto ws.Cells(r, COL_SCAN), False
    ws.Cells(r, COL_SCAN).Select
End Sub

Public Sub AddLine()
    Dim ws As Worksheet, r As Long
    Set ws = ThisWorkbook.Worksheets(SH_SELL)
    ws.Activate
    r = NextFreeRow()
    ws.Cells(r, COL_NEW).ClearContents        ' blank = same invoice as the line above
    ws.Cells(r, COL_DATE).Value = Date
    Application.Goto ws.Cells(r, COL_SCAN), False
    ws.Cells(r, COL_SCAN).Select
End Sub

'------------------------------------------------------- ONE TAP: PDF + SHARE
Public Sub GenerateInvoice()
    Dim wsI As Worksheet, inv As String, pdfPath As String, answer As VbMsgBoxResult

    Set wsI = ThisWorkbook.Worksheets(SH_INV)
    inv = CurrentInvoiceNo()

    If Len(inv) = 0 Then
        MsgBox "No invoice is selected." & vbCrLf & vbCrLf & _
               "Pick one in the SHOW INVOICE box, or leave it on LATEST.", _
               vbExclamation, "Nothing to generate"
        Exit Sub
    End If
    If Len(ThisWorkbook.Path) = 0 Then
        MsgBox "Save this workbook to a folder first - the PDF is written next to it.", _
               vbExclamation, "Workbook not saved yet"
        Exit Sub
    End If
    If wsI.Range("A12").Value = "" Then
        MsgBox "Invoice " & inv & " has no lines." & vbCrLf & vbCrLf & _
               "Enter the sale on the New Sale screen first.", vbExclamation, "Empty invoice"
        Exit Sub
    End If

    pdfPath = ThisWorkbook.Path & Application.PathSeparator & "Invoice-" & inv & ".pdf"

    On Error GoTo ExportFailed
    wsI.ExportAsFixedFormat Type:=xlTypePDF, Filename:=pdfPath, _
        Quality:=xlQualityStandard, IncludeDocProperties:=True, _
        IgnorePrintAreas:=False, OpenAfterPublish:=False
    On Error GoTo 0

    answer = MsgBox("Saved:" & vbCrLf & pdfPath & vbCrLf & vbCrLf & _
                    "Send it now?" & vbCrLf & vbCrLf & _
                    "YES  = WhatsApp" & vbCrLf & _
                    "NO   = Email with the PDF attached" & vbCrLf & _
                    "CANCEL = just keep the file", _
                    vbYesNoCancel + vbQuestion, "Invoice " & inv & " ready")

    Select Case answer
        Case vbYes:  SendWhatsApp
        Case vbNo:   SendEmailWithPDF pdfPath
    End Select
    Exit Sub

ExportFailed:
    MsgBox "Could not write the PDF." & vbCrLf & vbCrLf & _
           "Most often this means the file is already open, or the folder is " & _
           "read-only (OneDrive still syncing, for example)." & vbCrLf & vbCrLf & _
           "Details: " & Err.Description, vbCritical, "PDF export failed"
End Sub

Public Sub SendWhatsApp()
    Dim wsI As Worksheet, phone As String, url As String
    Set wsI = ThisWorkbook.Worksheets(SH_INV)
    phone = DigitsOnly(CStr(wsI.Range("B9").Value))
    If Len(phone) = 0 Then
        MsgBox "This customer has no phone number." & vbCrLf & vbCrLf & _
               "Add it in the Phone column of the Sales Log, on this invoice's row.", _
               vbExclamation, "No number to send to"
        Exit Sub
    End If
    url = "https://wa.me/" & phone & "?text=" & Replace(InvoiceText(), " ", "%20")
    ThisWorkbook.FollowHyperlink url
End Sub

Public Sub SendEmailWithPDF(Optional ByVal pdfPath As String = "")
    Dim wsI As Worksheet, olApp As Object, mail As Object
    Dim addr As String, body As String, shop As String

    Set wsI = ThisWorkbook.Worksheets(SH_INV)
    addr = Trim$(CStr(wsI.Range("D9").Value))
    shop = CStr(ThisWorkbook.Worksheets(SH_SET).Range("C8").Value)

    If Len(addr) = 0 Then
        MsgBox "This customer has no email address." & vbCrLf & vbCrLf & _
               "Add it in the Email column of the Sales Log, on this invoice's row.", _
               vbExclamation, "No address to send to"
        Exit Sub
    End If

    ' The share text is URL-encoded for WhatsApp; decode it back for a real email.
    body = InvoiceText()
    body = Replace(body, "%0A", vbCrLf)
    body = Replace(body, "%20", " ")
    body = Replace(body, "*", "")

    On Error GoTo NoOutlook
    Set olApp = CreateObject("Outlook.Application")
    Set mail = olApp.CreateItem(0)
    With mail
        .To = addr
        .Subject = "Invoice " & CurrentInvoiceNo() & " from " & shop
        .Body = body
        If Len(pdfPath) > 0 Then
            If Len(Dir$(pdfPath)) > 0 Then .Attachments.Add pdfPath
        End If
        .Display                       ' shows the draft; use .Send to fire it straight away
    End With
    Exit Sub

NoOutlook:
    ' No Outlook (common on Mac) - fall back to the default mail client.
    ThisWorkbook.FollowHyperlink "mailto:" & addr & _
        "?subject=" & Replace("Invoice " & CurrentInvoiceNo() & " from " & shop, " ", "%20") & _
        "&body=" & Replace(Replace(InvoiceText(), "%0A", "%0D%0A"), " ", "%20")
    If Len(pdfPath) > 0 Then
        MsgBox "Outlook is not available, so a plain mail draft was opened." & vbCrLf & vbCrLf & _
               "Attach the PDF manually from:" & vbCrLf & pdfPath, vbInformation, "Attach the PDF"
    End If
End Sub
