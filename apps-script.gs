/**
 * Google Apps Script for Kommunal Grundsalg Monitor
 * 
 * This script provides a webapp endpoint for reading from and writing to Google Sheets.
 * Deploy this as a web app to get the SHEETS_WEBAPP_URL.
 */

function doGet(e) {
  // Handle GET requests (e.g., when accessing URL in browser)
  return ContentService.createTextOutput(
    JSON.stringify({ 
      success: true, 
      message: "Sheets Webapp is running. Use POST requests with action: 'read' or 'append'",
      endpoint: "POST to this URL with JSON: { action: 'read'|'append', sheet: 'sheet_name', row: [...] }"
    })
  ).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const action = data.action;
    const sheetName = data.sheet;
    
    if (!sheetName) {
      return ContentService.createTextOutput(
        JSON.stringify({ success: false, error: "Sheet name is required" })
      ).setMimeType(ContentService.MimeType.JSON);
    }
    
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = spreadsheet.getSheetByName(sheetName);
    
    // Create sheet if it doesn't exist
    if (!sheet) {
      sheet = spreadsheet.insertSheet(sheetName);
    }
    
    if (action === "read") {
      const rows = sheet.getDataRange().getValues();
      return ContentService.createTextOutput(
        JSON.stringify({ success: true, data: rows })
      ).setMimeType(ContentService.MimeType.JSON);
      
    } else if (action === "append") {
      const row = data.row;
      if (!row || !Array.isArray(row)) {
        return ContentService.createTextOutput(
          JSON.stringify({ success: false, error: "Row must be an array" })
        ).setMimeType(ContentService.MimeType.JSON);
      }
      
      sheet.appendRow(row);
      return ContentService.createTextOutput(
        JSON.stringify({ success: true, message: "Row appended" })
      ).setMimeType(ContentService.MimeType.JSON);
      
    } else {
      return ContentService.createTextOutput(
        JSON.stringify({ success: false, error: `Unknown action: ${action}` })
      ).setMimeType(ContentService.MimeType.JSON);
    }
    
  } catch (error) {
    return ContentService.createTextOutput(
      JSON.stringify({ success: false, error: error.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}
