import AuthForm from "@/components/auth-form";

export default function SignUpPage() {
  return (
    <main className="mx-auto max-w-md p-6">
      <AuthForm mode="sign-up" />
    </main>
  );
}