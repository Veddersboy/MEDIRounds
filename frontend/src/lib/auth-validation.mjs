const MIN_PASSWORD_LENGTH = 8;

export function validateSignIn({ email, password } = {}) {
  const errors = {};

  if (!email?.trim()) {
    errors.email = "Email is required.";
  } else if (!isValidEmail(email.trim())) {
    errors.email = "Enter a valid email address.";
  }

  if (!password) {
    errors.password = "Password is required.";
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
}

export function validateSignUp({
  name,
  email,
  password,
  confirmPassword,
} = {}) {
  const errors = {};

  if (!name?.trim()) {
    errors.name = "Name is required.";
  }

  if (!email?.trim()) {
    errors.email = "Email is required.";
  } else if (!isValidEmail(email.trim())) {
    errors.email = "Enter a valid email address.";
  }

  if (!password) {
    errors.password = "Password is required.";
  } else if (password.length < MIN_PASSWORD_LENGTH) {
    errors.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }

  if (password !== confirmPassword) {
    errors.confirmPassword = "Passwords do not match.";
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
