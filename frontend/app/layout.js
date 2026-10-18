import "./globals.css";

export const metadata = {
  title: "Billo — Make every care dollar count",
  description: "Plan care, understand the bill, and organize what comes next.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
