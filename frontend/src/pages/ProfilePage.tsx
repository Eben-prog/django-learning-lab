import { useState, type FormEvent } from "react";
import { changePassword, updateMe } from "../api/auth";
import { describeError } from "../api/errors";
import { ErrorBanner, Field } from "../components/ui";
import { useAuth } from "../hooks/useAuth";

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({ first_name: user?.first_name ?? "", last_name: user?.last_name ?? "", email: user?.email ?? "" });
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [profileErr, setProfileErr] = useState<string | null>(null);
  const [profileFields, setProfileFields] = useState<Record<string, string>>({});

  const [pw, setPw] = useState({ old: "", next: "" });
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [pwFields, setPwFields] = useState<Record<string, string>>({});

  if (!user) return null;

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setProfileMsg(null);
    setProfileErr(null);
    setProfileFields({});
    try {
      setUser(await updateMe(form));
      setProfileMsg("Profile saved.");
    } catch (err) {
      const d = describeError(err);
      setProfileErr(d.message);
      setProfileFields(d.fields);
    }
  }

  async function savePassword(e: FormEvent) {
    e.preventDefault();
    setPwMsg(null);
    setPwErr(null);
    setPwFields({});
    try {
      await changePassword(pw.old, pw.next);
      setPw({ old: "", next: "" });
      setPwMsg("Password changed.");
    } catch (err) {
      const d = describeError(err);
      setPwErr(d.message);
      setPwFields(d.fields);
    }
  }

  return (
    <section className="two-col">
      <form className="panel" onSubmit={saveProfile}>
        <h1>Profile</h1>
        <p className="muted">
          Signed in as <strong>{user.username}</strong> ({user.role})
        </p>
        <ErrorBanner message={profileErr} />
        {profileMsg && <div className="banner ok">{profileMsg}</div>}
        <Field label="First name" error={profileFields.first_name}>
          <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
        </Field>
        <Field label="Last name" error={profileFields.last_name}>
          <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
        </Field>
        <Field label="Email" error={profileFields.email}>
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        </Field>
        <button className="btn primary">Save profile</button>
      </form>

      <form className="panel" onSubmit={savePassword}>
        <h2>Change password</h2>
        <ErrorBanner message={pwErr} />
        {pwMsg && <div className="banner ok">{pwMsg}</div>}
        <Field label="Current password" error={pwFields.old_password}>
          <input type="password" value={pw.old} onChange={(e) => setPw({ ...pw, old: e.target.value })} autoComplete="current-password" required />
        </Field>
        <Field label="New password" error={pwFields.new_password}>
          <input type="password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} autoComplete="new-password" required />
        </Field>
        <button className="btn primary">Change password</button>
      </form>
    </section>
  );
}
