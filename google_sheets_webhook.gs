function doPost(event) {
  try {
    const properties = PropertiesService.getScriptProperties();
    const expectedToken = properties.getProperty("SHEETS_WEBHOOK_SECRET") || "";
    const spreadsheetId = properties.getProperty("SHEETS_SPREADSHEET_ID") || "";
    const requestText = event && event.postData && event.postData.contents;

    if (!expectedToken || expectedToken.length < 32 || !spreadsheetId || !requestText || requestText.length > 8192) {
      return jsonResponse({ ok: false });
    }

    const payload = JSON.parse(requestText);
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return jsonResponse({ ok: false });
    }

    const allowedFields = new Set(["token", "submitted", "name", "email", "phone", "business", "service", "message"]);
    if (Object.keys(payload).some(function(field) { return !allowedFields.has(field); })) {
      return jsonResponse({ ok: false });
    }
    if (!constantTimeEquals(String(payload.token || ""), expectedToken) || payload.submitted !== true) {
      return jsonResponse({ ok: false });
    }

    const name = validateText(payload.name, 100, true);
    const email = validateText(payload.email, 254, true);
    const phone = validateText(payload.phone, 40, false);
    const business = validateText(payload.business, 140, false);
    const service = validateText(payload.service, 80, true);
    const message = validateText(payload.message, 4000, true);
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      return jsonResponse({ ok: false });
    }

    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
      const inquiriesSheet = spreadsheet.getSheetByName("Inquiries") || spreadsheet.insertSheet("Inquiries");
      if (inquiriesSheet.getLastRow() === 0) {
        inquiriesSheet.appendRow(["Received at", "Name", "Email", "Phone", "Business", "Service", "Project details"]);
        inquiriesSheet.setFrozenRows(1);
      }

      const receivedAt = new Date();
      const inquiryRow = inquiriesSheet.getLastRow() + 1;
      inquiriesSheet.getRange(inquiryRow, 1, 1, 7).setValues([[
        receivedAt,
        safeSheetText(name),
        safeSheetText(email),
        safeSheetText(phone),
        safeSheetText(business),
        safeSheetText(service),
        safeSheetText(message),
      ]]);
      inquiriesSheet.getRange(inquiryRow, 1).setNumberFormat("yyyy-mm-dd hh:mm:ss");
      inquiriesSheet.getRange(inquiryRow, 2, 1, 6).setNumberFormat("@");

      const contactsSheet = spreadsheet.getSheetByName("Contacts") || spreadsheet.insertSheet("Contacts");
      if (contactsSheet.getLastRow() === 0) {
        contactsSheet.appendRow(["Received at", "Name", "Email", "Phone", "Business", "Service"]);
        contactsSheet.setFrozenRows(1);
      }

      const contactRow = contactsSheet.getLastRow() + 1;
      contactsSheet.getRange(contactRow, 1, 1, 6).setValues([[
        receivedAt,
        safeSheetText(name),
        safeSheetText(email),
        safeSheetText(phone),
        safeSheetText(business),
        safeSheetText(service),
      ]]);
      contactsSheet.getRange(contactRow, 1).setNumberFormat("yyyy-mm-dd hh:mm:ss");
      contactsSheet.getRange(contactRow, 2, 1, 5).setNumberFormat("@");
    } finally {
      lock.releaseLock();
    }

    return jsonResponse({ ok: true });
  } catch (error) {
    return jsonResponse({ ok: false });
  }
}

function validateText(value, maxLength, required) {
  if (typeof value !== "string") {
    throw new Error("Invalid field.");
  }
  const text = value.trim();
  if ((required && !text) || text.length > maxLength || /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/.test(text)) {
    throw new Error("Invalid field.");
  }
  return text;
}

function safeSheetText(value) {
  return /^[\s]*[=+\-@]/.test(value) ? "'" + value : value;
}

function constantTimeEquals(left, right) {
  const leftDigest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, left, Utilities.Charset.UTF_8);
  const rightDigest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, right, Utilities.Charset.UTF_8);
  let difference = leftDigest.length ^ rightDigest.length;
  for (let index = 0; index < leftDigest.length; index += 1) {
    difference |= leftDigest[index] ^ rightDigest[index];
  }
  return difference === 0;
}

function jsonResponse(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}