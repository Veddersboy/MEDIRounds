import { AppProvider } from "@/components/app-provider";
import { Shell } from "@/components/shell";

// App pages get the data provider and the sidebar shell; the auth pages don't.
export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AppProvider>
      <Shell>{children}</Shell>
    </AppProvider>
  );
}
