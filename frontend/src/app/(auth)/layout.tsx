// Sign-in and sign-up render without the app shell, centered on the page.
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col justify-center">
      {children}
    </div>
  );
}
