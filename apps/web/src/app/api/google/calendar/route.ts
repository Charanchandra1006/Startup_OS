import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const token = req.headers.get("Authorization");
  if (!token) {
    return NextResponse.json({ error: "Missing Authorization header" }, { status: 401 });
  }

  const maxResults = req.nextUrl.searchParams.get("maxResults") || "8";
  const now = new Date().toISOString();

  try {
    const calRes = await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin=${encodeURIComponent(now)}&maxResults=${maxResults}&orderBy=startTime&singleEvents=true`,
      { headers: { Authorization: token } }
    );

    if (!calRes.ok) {
      const errBody = await calRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: "Google Calendar API rejected the token", detail: errBody, status: calRes.status },
        { status: calRes.status }
      );
    }

    const data = await calRes.json();

    const events = (data.items || []).map((item: any, i: number) => {
      const start = item.start?.dateTime
        ? new Date(item.start.dateTime)
        : item.start?.date
        ? new Date(item.start.date)
        : new Date();
      const end = item.end?.dateTime
        ? new Date(item.end.dateTime)
        : item.end?.date
        ? new Date(item.end.date)
        : new Date(start.getTime() + 30 * 60000);
      const durationMins = Math.max(Math.round((end.getTime() - start.getTime()) / 60000), 15);
      const timeStr = start.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
      const attendees = item.attendees
        ? item.attendees.map((a: any) => a.displayName || a.email.split("@")[0]).slice(0, 4)
        : ["Charan Chandra"];

      return {
        id: item.id || `live-${i}`,
        time: timeStr,
        title: item.summary || "(No Title)",
        type: "Google Calendar",
        duration: `${durationMins} min`,
        attendees,
        location: item.location || item.hangoutLink || "Google Meet / Online",
        status: i === 0 ? "In Progress" : "Upcoming",
        briefing:
          item.description ||
          `Live Google Calendar event. Organizer: ${item.organizer?.email || "Self"}.`,
        htmlLink: item.htmlLink,
      };
    });

    return NextResponse.json({ events, live: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal proxy error" }, { status: 500 });
  }
}
