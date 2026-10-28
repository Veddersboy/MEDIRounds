// Dev-only endpoint for checking that outgoing mail is caught by Mailpit.
// Visit http://localhost:3000/api/dev/test-email (optionally ?to=someone@example.com)
// then open the Mailpit inbox at http://localhost:8025

import { NextRequest } from "next/server";
import { sendMail } from "@/lib/mailer";

export async function GET(request: NextRequest) {
    // Never expose this outside of local development
    if (process.env.NODE_ENV !== "development") {
        return new Response("Not Found", { status: 404 });
    }

    const to = request.nextUrl.searchParams.get("to") ?? "test@medirounds.local";
    const sentAt = new Date().toISOString();

    try {
        await sendMail({
            to,
            subject: "MEDIRounds test email",
            html: `<p>If you can read this in Mailpit, SMTP is wired up correctly.</p><p>Sent at ${sentAt}</p>`,
            text: `If you can read this in Mailpit, SMTP is wired up correctly.\nSent at ${sentAt}`,
        });
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return Response.json({ ok: false, error: message }, { status: 500 });
    }

    return Response.json({ ok: true, to, sentAt, inbox: "http://localhost:8025" });
}
