import { supabase } from "./supabase";
import type { Account } from "./api";
import { followerTier } from "./api";

export interface Group {
  id: string;
  name: string;
  created_at: string;
  member_count?: number;
}

export interface GroupMember {
  id: string;
  group_id: string;
  account_id: string;
  handle: string | null;
  display_name: string | null;
  platform: string | null;
  profile_url: string | null;
  follower_count: number | null;
  tier: number | null;
  niche: string | null;
  contact_email: string | null;
  added_at: string;
}

export async function listGroups(): Promise<Group[]> {
  const { data, error } = await supabase
    .from("groups")
    .select("id, name, created_at, group_members(count)")
    .order("created_at", { ascending: false });
  if (error) throw error;
  return (data ?? []).map((g: any) => ({
    id: g.id,
    name: g.name,
    created_at: g.created_at,
    member_count: g.group_members?.[0]?.count ?? 0,
  }));
}

export async function createGroup(name: string): Promise<Group> {
  const { data, error } = await supabase
    .from("groups")
    .insert({ name })
    .select("id, name, created_at")
    .single();
  if (error) throw error;
  return { ...data, member_count: 0 } as Group;
}

export async function renameGroup(id: string, name: string): Promise<void> {
  const { error } = await supabase.from("groups").update({ name }).eq("id", id);
  if (error) throw error;
}

export async function deleteGroup(id: string): Promise<void> {
  const { error } = await supabase.from("groups").delete().eq("id", id);
  if (error) throw error;
}

export async function listGroupMembers(groupId: string): Promise<GroupMember[]> {
  const { data, error } = await supabase
    .from("group_members")
    .select("*")
    .eq("group_id", groupId)
    .order("added_at", { ascending: false });
  if (error) throw error;
  return (data ?? []) as GroupMember[];
}

export async function removeMember(memberId: string): Promise<void> {
  const { error } = await supabase.from("group_members").delete().eq("id", memberId);
  if (error) throw error;
}

/** Add the given accounts to a group. Ignores ones already present (unique constraint). */
export async function addAccountsToGroup(
  groupId: string,
  accounts: Account[]
): Promise<number> {
  const userRes = await supabase.auth.getUser();
  const userId = userRes.data.user?.id;
  if (!userId) throw new Error("Not signed in");

  const rows = accounts.map((a) => ({
    group_id: groupId,
    user_id: userId,
    account_id: a.account_id,
    handle: a.display_handle || a.handle,
    display_name: a.display_name,
    platform: a.platform,
    profile_url: a.profile_url,
    follower_count: a.follower_count,
    tier: a.tier ?? followerTier(a.follower_count),
    niche: a.niche,
    contact_email: a.contact_email ?? null,
  }));

  // upsert on (group_id, account_id) so re-adding is a no-op instead of an error.
  const { data, error } = await supabase
    .from("group_members")
    .upsert(rows, { onConflict: "group_id,account_id", ignoreDuplicates: true })
    .select("id");
  if (error) throw error;
  return data?.length ?? 0;
}
