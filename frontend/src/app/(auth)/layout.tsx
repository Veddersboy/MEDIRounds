import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { auth } from "@/src/lib/auth";

// Sign-in and sign-up render without the app shell, centered on the page.
export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // No signed-in user should be on the signin page. Redirect them to the main page
  const session = await auth.api.getSession({ headers: await headers() });
  if (session) { redirect("/"); }
  
  return (
    <div className="flex min-h-screen flex-col justify-center">
      {children}
    </div>
  );
}
