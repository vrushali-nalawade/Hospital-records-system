"use client";

import { useState } from "react";
import { User, Phone, Calendar, Heart, Mail, Edit2, Check, X } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import PreferencesSection from "@/components/ui/PreferencesSection";
import { useAuth } from "@/context/auth-context";
import { useI18n } from "@/context/i18n-context";
import { pushToast } from "@/components/ui/Toast";

export default function PatientProfilePage() {
  const { user, setUser } = useAuth();
  const { t } = useI18n();

  const [isEditing, setIsEditing] = useState(false);
  const [fullName, setFullName] = useState(user?.fullName || "");
  const [phone, setPhone] = useState(user?.phone || "+91 98765 43210");
  const [dateOfBirth, setDateOfBirth] = useState(user?.dateOfBirth || "1995-05-15");
  const [gender, setGender] = useState(user?.gender || "other");

  if (!user || user.role !== "patient") return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const updated = {
      ...user,
      fullName: fullName.trim() || user.fullName,
      phone: phone.trim(),
      dateOfBirth: dateOfBirth.trim(),
      gender: gender as any,
    };
    setUser(updated);
    setIsEditing(false);
    pushToast({
      type: "success",
      message: "Profile updated successfully!",
    });
  };

  const handleCancel = () => {
    setFullName(user.fullName || "");
    setPhone(user.phone || "");
    setDateOfBirth(user.dateOfBirth || "");
    setGender(user.gender || "other");
    setIsEditing(false);
  };

  return (
    <DashboardShell role="patient" title={t("profile")}>
      <Card className="max-w-xl p-6">
        <div className="mb-6 flex items-center justify-between border-b border-slate-100 pb-5">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-teal-600 text-lg font-semibold text-white shadow-sm">
              {user.fullName.charAt(0)}
            </div>
            <div>
              <p className="font-semibold text-slate-900">{user.fullName}</p>
              <p className="text-sm text-slate-500">{user.email}</p>
            </div>
          </div>
          {!isEditing && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setFullName(user.fullName || "");
                setPhone(user.phone || "");
                setDateOfBirth(user.dateOfBirth || "");
                setGender(user.gender || "other");
                setIsEditing(true);
              }}
              className="inline-flex items-center gap-1.5"
            >
              <Edit2 className="h-3.5 w-3.5" /> Edit Profile
            </Button>
          )}
        </div>

        {isEditing ? (
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">Phone Number</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 98765 43210"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">Date of Birth</label>
              <input
                type="date"
                value={dateOfBirth}
                onChange={(e) => setDateOfBirth(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">Gender</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value as any)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="flex gap-2 pt-2">
              <Button type="submit" size="sm" className="inline-flex items-center gap-1">
                <Check className="h-4 w-4" /> Save Changes
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={handleCancel} className="inline-flex items-center gap-1">
                <X className="h-4 w-4" /> Cancel
              </Button>
            </div>
          </form>
        ) : (
          <dl className="divide-y divide-slate-100">
            <div className="flex items-center justify-between py-3 text-sm">
              <dt className="text-slate-500 flex items-center gap-2"><User className="h-4 w-4 text-slate-400" /> Full Name</dt>
              <dd className="font-medium text-slate-800">{user.fullName}</dd>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <dt className="text-slate-500 flex items-center gap-2"><Mail className="h-4 w-4 text-slate-400" /> Email</dt>
              <dd className="font-medium text-slate-800">{user.email}</dd>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <dt className="text-slate-500 flex items-center gap-2"><Phone className="h-4 w-4 text-slate-400" /> Phone</dt>
              <dd className="font-medium text-slate-800">{user.phone || "Not set"}</dd>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <dt className="text-slate-500 flex items-center gap-2"><Calendar className="h-4 w-4 text-slate-400" /> Date of Birth</dt>
              <dd className="font-medium text-slate-800">{user.dateOfBirth || "Not set"}</dd>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <dt className="text-slate-500 flex items-center gap-2"><Heart className="h-4 w-4 text-slate-400" /> Gender</dt>
              <dd className="font-medium capitalize text-slate-800">{user.gender || "Not specified"}</dd>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <dt className="text-slate-500">Account Created</dt>
              <dd className="font-medium text-slate-800">{new Date(user.createdAt).toLocaleDateString("en-IN")}</dd>
            </div>
          </dl>
        )}

        <PreferencesSection />
      </Card>
    </DashboardShell>
  );
}
