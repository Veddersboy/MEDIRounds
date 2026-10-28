// A lightweight SMTP mailer module using the nodemailer library
// In production, we could either use this or the ReSend SDK (by checking if
// a resend api key exists, or something like that)

import nodemailer from "nodemailer"

// Configures the transporter accourding to the process's environment
const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT ?? 1025),
    secure: process.env.SMTP_SECURE === "true",
    auth: process.env.SMTP_USER
        ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS }
        : undefined,
});

export async function sendMail( opts: {
    to: string;
    subject: string;
    html: string;
    text?: string;
}) {
    await transporter.sendMail({ from: process.env.MAIL_FROM, ...opts });
}