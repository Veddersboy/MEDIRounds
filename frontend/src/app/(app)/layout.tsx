import { AppProvider } from "@/components/app-provider";
import { Shell } from "@/components/shell";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { auth } from "@/src/lib/auth";

// App pages get the data provider and the sidebar shell; the auth pages don't.
export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Attempt to grab a session, and redirect to signin if one is not found
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) { redirect("/sign-in"); }

  const { id, name, email } = session.user;
  return (
    <AppProvider user={{ id, name, email }} >
      <Shell>{children}</Shell>
    </AppProvider>
  );
}
