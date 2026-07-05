import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const token = req.headers.get("Authorization");
  if (!token) {
    return NextResponse.json({ error: "Missing Authorization header" }, { status: 401 });
  }

  const maxResults = req.nextUrl.searchParams.get("maxResults") || "6";

  try {
    const listRes = await fetch(
      `https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=${maxResults}&labelIds=INBOX`,
      { headers: { Authorization: token } }
    );

    if (!listRes.ok) {
      const errBody = await listRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: "Gmail API rejected the token", detail: errBody, status: listRes.status },
        { status: listRes.status }
      );
    }

    const listData = await listRes.json();

    if (!listData.messages || listData.messages.length === 0) {
      return NextResponse.json({ messages: [], live: true });
    }

    // Fetch detail for each message in parallel (up to 5)
    const ids: string[] = listData.messages.slice(0, 5).map((m: any) => m.id);
    const detailResults = await Promise.all(
      ids.map((id) =>
        fetch(`https://gmail.googleapis.com/gmail/v1/users/me/messages/${id}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date`, {
          headers: { Authorization: token },
        }).then((r) => (r.ok ? r.json() : null))
      )
    );

    const messages = detailResults
      .filter(Boolean)
      .map((detail: any) => {
        const headers = detail.payload?.headers || [];
        const getH = (name: string) =>
          headers.find((h: any) => h.name.toLowerCase() === name.toLowerCase())?.value || "";
        const from = getH("From");
        const senderName = from.includes("<") ? from.split("<")[0].trim() : from.split("@")[0];
        const senderEmail = from.includes("<") ? from.split("<")[1].replace(">", "").trim() : from;
        return {
          id: detail.id,
          sender: senderName || "Unknown Sender",
          senderEmail,
          subject: getH("Subject") || "(No Subject)",
          dateHeader: getH("Date"),
          snippet: detail.snippet || "No preview available.",
          unread: detail.labelIds?.includes("UNREAD") ?? false,
        };
      });

    return NextResponse.json({ messages, live: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal proxy error" }, { status: 500 });
  }
}
