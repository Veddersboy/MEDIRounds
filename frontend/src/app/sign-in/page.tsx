import AuthForm from "@/components/auth-form";

export default function SignInPage() {
  return (
    <main className="mx-auto max-w-md p-6">
      <AuthForm mode="sign-in" />
    </main>
  );
}