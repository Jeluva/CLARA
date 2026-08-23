import type {
  ReactNode,
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

const baseControl =
  "w-full rounded-control border border-separator bg-bg px-3 py-2 text-sm " +
  "text-primary placeholder:text-secondary focus:border-accent focus:outline-none " +
  "transition-colors duration-150";

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-secondary">{label}</span>
      {children}
    </label>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={baseControl} />;
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${baseControl} resize-y`} />;
}

export function Select({
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select {...props} className={baseControl}>
      {children}
    </select>
  );
}

export function Button({
  children,
  variant = "primary",
  ...props
}: {
  variant?: "primary" | "ghost" | "danger";
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = {
    primary: "bg-accent text-white hover:bg-accent/90",
    ghost: "border border-separator text-primary hover:bg-separator/40",
    danger: "text-loss hover:bg-loss/10",
  }[variant];
  return (
    <button
      {...props}
      className={[
        "rounded-control px-4 py-2 text-sm font-medium transition-colors duration-150 disabled:opacity-50",
        styles,
      ].join(" ")}
    >
      {children}
    </button>
  );
}
