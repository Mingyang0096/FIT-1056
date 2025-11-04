# app/service.py
from __future__ import annotations
from typing import List, Optional, Tuple, Set, Any
from datetime import datetime, timezone, timedelta
import hashlib, uuid, csv, io, re

from app.utils import now_iso, check_range

LOCKOUT_LIMIT = 5
LOCKOUT_MINUTES = 10

class CareLogService:
    def __init__(self, repo):
        self.repo = repo
        self.data = repo.load()

    # ===== NEW: searchable types for the unified iterator/selector =====
    # Entity types supported on the Search page (pluralized to match bucket keys)
    SEARCHABLE_TYPES: Set[str] = {"observations", "stories", "visits", "preferences", "handover_notes"}

    # ---------- id helpers ----------
    def _ensure_next_ids(self):
        self.data.setdefault("next_ids", {"patient":1,"visit":1,"observation":1,"story":1,"handover":1})
        for key, pref in [("patients","P"),("visits","V"),("observations","O"),("stories","S"),("handover_notes","H")]:
            max_id = 0
            for x in self.data.get(key, []):
                try:
                    num = int(x["id"][1:])
                    if num > max_id: max_id = num
                except: pass
            base = {"P":"patient","V":"visit","O":"observation","S":"story","H":"handover"}[pref]
            self.data["next_ids"][base] = max(self.data["next_ids"].get(base,1), max_id+1)

    def _new_id(self, kind:str, prefix:str) -> str:
        self._ensure_next_ids()
        n = self.data["next_ids"].get(kind, 1)
        self.data["next_ids"][kind] = n+1
        return f"{prefix}{n}"

    # ---------- audit ----------
    def _audit(self, actor:str, action:str, meta:Optional[dict]=None):
        self.data.setdefault("audit", [])
        self.data["audit"].append({
            "id": self._new_id("audit","A"),
            "ts": now_iso(),
            "actor": actor,
            "action": action,
            "meta": meta or {}
        })

    def _get_user(self, username:str) -> Optional[dict]:
        return next((x for x in self.data["users"] if x["username"]==username), None)

    def _role(self, username:str) -> Optional[str]:
        u = self._get_user(username)
        return u["role"] if u else None

    def get_assigned_patient_ids(self, username:str) -> List[str]:
        return [a["patient_id"] for a in self.data.get("assignments", []) if a["username"]==username]

    def get_patient_info_for_user(self, username:str) -> Optional[dict]:
        """Get patient record information for a user (typically for Patient role)."""
        patient_ids = self.get_assigned_patient_ids(username)
        if not patient_ids:
            return None
        # Return the first assigned patient (typically patients have one record)
        pid = patient_ids[0]
        try:
            patient = self._get_patient(pid)
            return {"id": patient["id"], "name": patient.get("name", ""), "dob": patient.get("dob", "")}
        except:
            return None

    # ---------- NEW: list users for UI ----------
    def list_users(self, roles: Optional[List[str]] = None, only_enabled: bool = True) -> List[dict]:
        """Return a list of users with optional role filtering."""
        users = list(self.data.get("users", []))
        if roles:
            users = [u for u in users if u.get("role") in roles]
        if only_enabled:
            users = [u for u in users if not u.get("disabled", False)]
        # Keep minimal fields for UI
        return [{"username": u.get("username",""), "role": u.get("role",""), "disabled": u.get("disabled", False)} for u in users]

    # ---------- auth ----------
    def authenticate(self, username:str, password:str) -> dict:
        self.data.setdefault("users", [])
        u = next((x for x in self.data["users"] if x["username"]==username), None)
        if not u: raise PermissionError("invalid credentials")
        if u.get("disabled"): raise PermissionError("account disabled")

        # lockout
        if u.get("locked_until"):
            until = datetime.fromisoformat(u["locked_until"])
            if datetime.now(timezone.utc).astimezone() < until:
                raise PermissionError("account locked temporarily")

        salt = u["salt"]
        hashv = hashlib.sha256((salt+password).encode()).hexdigest()
        if hashv != u["hash"]:
            u["failed_attempts"] = u.get("failed_attempts", 0) + 1
            if u["failed_attempts"] >= LOCKOUT_LIMIT:
                u["locked_until"] = (datetime.now(timezone.utc).astimezone() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            self.repo.save(self.data)
            raise PermissionError("invalid credentials")

        # success
        u["failed_attempts"] = 0
        u["locked_until"] = None
        self.repo.save(self.data)
        self._audit(username, "login")
        return {"username": username, "role": u["role"]}

    def self_register(self, username:str, password:str, role:str) -> dict:
        allowed = {"Admin", "Auditor", "Nurse", "Doctor", "Patient"}
        if not username or not password:
            raise ValueError("username and password required")
        if role not in allowed:
            raise ValueError("invalid role")
        if any(u["username"]==username for u in self.data["users"]):
            raise ValueError("username exists")

        self._create_user("self-register", username, password, role)

        if role == "Patient":
            pid = self.create_patient(name=username, dob=None, tags=["self"])
            self.data.setdefault("assignments", [])
            if not any(a for a in self.data["assignments"] if a["patient_id"]==pid and a["username"]==username):
                self.data["assignments"].append({"patient_id": pid, "username": username})
                self._audit(username, "assign_self", {"patient_id": pid})
                self.repo.save(self.data)

        return {"username": username, "role": role}

    # ---------- authorization helpers ----------
    def _require_role(self, actor:str, roles:List[str]):
        au = self._get_user(actor)
        if not au or au["role"] not in roles:
            raise PermissionError("insufficient role")

    def _ensure_can_write(self, actor:str):
        au = self._get_user(actor)
        if not au or au["role"] not in ("Admin","Nurse","Doctor"):
            raise PermissionError("insufficient role")

    def can_access(self, username:str, patient_id:str) -> bool:
        role = self._role(username)
        if role in ("Admin","Auditor"): return True
        if role in ("Nurse","Doctor"):
            return any(a for a in self.data.get("assignments", []) if a["patient_id"]==patient_id and a["username"]==username)
        if role == "Patient":
            return any(a for a in self.data.get("assignments", []) if a["patient_id"]==patient_id and a["username"]==username)
        return False

    # ---------- user admin ----------
    def _create_user(self, actor:str, username:str, password:str, role:str):
        salt = uuid.uuid4().hex
        hashv = hashlib.sha256((salt+password).encode()).hexdigest()
        self.data.setdefault("users", []).append({"username":username,"salt":salt,"hash":hashv,"role":role,"disabled":False})
        self.repo.save(self.data)
        self._audit(actor, "create_user", {"username":username,"role":role})

    def admin_create_user(self, actor:str, username:str, password:str, role:str):
        self._require_role(actor, ["Admin"])
        if any(u["username"]==username for u in self.data.get("users", [])):
            raise ValueError("username exists")
        self._create_user(actor, username, password, role)

    def admin_disable_user(self, actor:str, username:str, disabled:bool):
        self._require_role(actor, ["Admin"])
        u = self._get_user(username)
        if not u: raise ValueError("user not found")
        u["disabled"] = disabled
        self.repo.save(self.data)
        self._audit(actor, "disable_user", {"username": username, "disabled": disabled})

    # ---------- assignments ----------
    def assign_patient(self, username:str, patient_id:str):
        # self-assign
        self._ensure_can_write(username)
        self._get_patient(patient_id)
        self.data.setdefault("assignments", [])
        if not any(a for a in self.data["assignments"] if a["patient_id"]==patient_id and a["username"]==username):
            self.data["assignments"].append({"patient_id": patient_id, "username": username})
            self.repo.save(self.data)
            self._audit(username, "assign_self", {"patient_id": patient_id})

    def admin_assign_patient(self, actor:str, username:str, patient_id:str):
        self._require_role(actor, ["Admin"])
        self._get_patient(patient_id)
        self.data.setdefault("assignments", [])
        if not any(a for a in self.data["assignments"] if a["patient_id"]==patient_id and a["username"]==username):
            self.data["assignments"].append({"patient_id": patient_id, "username": username})
            self.repo.save(self.data)
            self._audit(actor, "assign_user", {"patient_id": patient_id, "username": username})

    # ---------- patients ----------
    def create_patient(self, name:str, dob:Optional[str], tags:Optional[List[str]]) -> str:
        pid = self._new_id("patient","P")
        self.data.setdefault("patients", []).append({
            "id": pid, "name": name or "", "dob": dob or "", "tags": tags or [],
            "created_at": now_iso(), "updated_at": now_iso(), "deleted": False
        })
        self.repo.save(self.data)
        return pid

    def edit_patient(self, pid:str, name:Optional[str]=None, dob:Optional[str]=None, tags:Optional[List[str]]=None):
        p = self._get_patient(pid)
        if name is not None: p["name"] = name
        if dob is not None: p["dob"] = dob
        if tags is not None: p["tags"] = tags
        self.repo.save(self.data)

    def soft_delete_patient(self, pid:str):
        p = self._get_patient(pid); p["deleted"] = True
        self.repo.save(self.data)

    def search_patients(self, kw:str):
        kw = (kw or "").lower()
        res = []
        for p in self.data.get("patients", []):
            if p.get("deleted"): continue
            hay = " ".join([p.get("name",""), " ".join(p.get("tags",[]))]).lower()
            if kw in hay:
                res.append(p)
        return res

    def get_all_patients(self):
        """Get all non-deleted patients."""
        return [p for p in self.data.get("patients", []) if not p.get("deleted")]

    def _get_patient(self, pid:str) -> dict:
        p = next((x for x in self.data.get("patients", []) if x["id"]==pid and not x.get("deleted")), None)
        if not p: raise ValueError("patient not found")
        return p

    # ---------- visits ----------
    def add_visit(self, pid:str, start:Optional[str]=None, username:Optional[str]=None) -> str:
        self._get_patient(pid)
        vid = self._new_id("visit","V")
        self.data.setdefault("visits", []).append({"id": vid, "patient_id": pid, "start": start or now_iso(), "end": None, "created_by": username or "system", "created_at": now_iso()})
        self.repo.save(self.data)
        return vid

    # ---------- observations ----------
    def add_observation(self, username:str, pid:str, vid:str, pain:int, appetite:str, note:str) -> str:
        self._ensure_can_write(username)
        if not self.can_access(username, pid):
            raise PermissionError("no access to patient")

        check_range(pain, 0, 10)
        if appetite not in ("Good","Average","Poor"):
            raise ValueError("invalid appetite")

        oid = self._new_id("observation","O")
        self.data.setdefault("observations", []).append({
            "id": oid, "patient_id": pid, "visit_id": vid,
            "pain": int(pain), "appetite": appetite, "note": note or "",
            "created_by": username, "created_at": now_iso(), "deleted": False
        })
        self.repo.save(self.data)
        self._audit(username, "add_observation", {"patient_id": pid, "id": oid})
        return oid

    def edit_observation(self, oid:str, pain:Optional[int]=None, appetite:Optional[str]=None, note:Optional[str]=None):
        o = next((x for x in self.data.get("observations", []) if x["id"]==oid), None)
        if not o: raise ValueError("observation not found")
        if pain is not None:
            check_range("pain", pain, 0, 10); o["pain"] = int(pain)
        if appetite is not None:
            if appetite not in ("Good","Average","Poor"):
                raise ValueError("invalid appetite")
            o["appetite"] = appetite
        if note is not None: o["note"] = note
        self.repo.save(self.data)

    def soft_delete_observation(self, oid:str):
        o = next((x for x in self.data.get("observations", []) if x["id"]==oid), None)
        if not o: raise ValueError("observation not found")
        o["deleted"] = True
        self.repo.save(self.data)

    def list_recent_observations(
        self,
        days:int=90,
        username:Optional[str]=None,
        patient_id:Optional[str]=None,
        deleted:Optional[bool]=False,
    ):
        cutoff = datetime.now(timezone.utc).astimezone() - timedelta(days=days)
        allowed_pids = None
        if username and self._role(username) not in ("Admin","Auditor"):
            allowed_pids = set(self.get_assigned_patient_ids(username))
        res = []
        for o in self.data.get("observations", []):
            is_deleted = o.get("deleted", False)
            if deleted is False and is_deleted:
                continue
            if deleted is True and not is_deleted:
                continue
            if patient_id and o.get("patient_id") != patient_id: continue
            if allowed_pids is not None and o["patient_id"] not in allowed_pids: continue
            ts = datetime.fromisoformat(o["created_at"])
            if ts >= cutoff:
                res.append(o)
        res.sort(key=lambda x: x["created_at"], reverse=True)
        return res

    def list_history_observations(
        self,
        before_days:int=90,
        username:Optional[str]=None,
        patient_id:Optional[str]=None,
        deleted:Optional[bool]=False,
    ):
        cutoff = datetime.now(timezone.utc).astimezone() - timedelta(days=before_days)
        allowed_pids = None
        if username and self._role(username) not in ("Admin","Auditor"):
            allowed_pids = set(self.get_assigned_patient_ids(username))
        res = []
        for o in self.data.get("observations", []):
            is_deleted = o.get("deleted", False)
            if deleted is False and is_deleted:
                continue
            if deleted is True and not is_deleted:
                continue
            if patient_id and o.get("patient_id") != patient_id: continue
            if allowed_pids is not None and o["patient_id"] not in allowed_pids: continue
            ts = datetime.fromisoformat(o["created_at"])
            if ts < cutoff:
                res.append(o)
        res.sort(key=lambda x: x["created_at"], reverse=True)
        return res

    # ---------- stories ----------
    def add_story(self, username:str, pid:str, vid:str, text:str) -> str:
        self._ensure_can_write(username)
        if not self.can_access(username, pid):
            raise PermissionError("no access to patient")
        sid = self._new_id("story","S")
        self.data.setdefault("stories", []).append({
            "id": sid, "patient_id": pid, "visit_id": vid,
            "text": text or "", "created_by": username, "created_at": now_iso(), "deleted": False
        })
        self.repo.save(self.data)
        self._audit(username, "add_story", {"patient_id": pid, "id": sid})
        return sid

    def edit_story(self, sid:str, text:str):
        s = next((x for x in self.data.get("stories", []) if x["id"]==sid), None)
        if not s: raise ValueError("story not found")
        s["text"] = text or ""
        self.repo.save(self.data)

    def soft_delete_story(self, actor:str, sid:str):
        s = next((x for x in self.data.get("stories", []) if x["id"]==sid), None)
        if not s: raise ValueError("story not found")
        if s.get("deleted"):
            return
        actor_name = actor or "system"
        s["deleted"] = True
        s["deleted_at"] = now_iso()
        s["deleted_by"] = actor_name
        self.repo.save(self.data)
        self._audit(actor_name, "delete_story", {"patient_id": s.get("patient_id"), "id": sid, "soft": True})

    def list_recent_stories(
        self,
        days:int=90,
        username:Optional[str]=None,
        patient_id:Optional[str]=None,
        deleted:Optional[bool]=False,
    ):
        cutoff = datetime.now(timezone.utc).astimezone() - timedelta(days=days)
        allowed_pids = None
        if username and self._role(username) not in ("Admin","Auditor"):
            allowed_pids = set(self.get_assigned_patient_ids(username))
        res = []
        for s in self.data.get("stories", []):
            is_deleted = s.get("deleted", False)
            if deleted is False and is_deleted:
                continue
            if deleted is True and not is_deleted:
                continue
            if patient_id and s.get("patient_id") != patient_id: continue
            if allowed_pids is not None and s["patient_id"] not in allowed_pids: continue
            ts = datetime.fromisoformat(s["created_at"])
            if ts >= cutoff:
                res.append(s)
        res.sort(key=lambda x: x["created_at"], reverse=True)
        return res

    def list_history_stories(
        self,
        before_days:int=90,
        username:Optional[str]=None,
        patient_id:Optional[str]=None,
        deleted:Optional[bool]=False,
    ):
        cutoff = datetime.now(timezone.utc).astimezone() - timedelta(days=before_days)
        allowed_pids = None
        if username and self._role(username) not in ("Admin","Auditor"):
            allowed_pids = set(self.get_assigned_patient_ids(username))
        res = []
        for s in self.data.get("stories", []):
            is_deleted = s.get("deleted", False)
            if deleted is False and is_deleted:
                continue
            if deleted is True and not is_deleted:
                continue
            if patient_id and s.get("patient_id") != patient_id: continue
            if allowed_pids is not None and s["patient_id"] not in allowed_pids: continue
            ts = datetime.fromisoformat(s["created_at"])
            if ts < cutoff:
                res.append(s)
        res.sort(key=lambda x: x["created_at"], reverse=True)
        return res

    # ---------- preferences ----------
    def upsert_preferences(self, pid:str, diet:Optional[str], gender:Optional[str], visiting_hours:Optional[str], staff_reader:Optional[str]=None, actor:Optional[str]=None):
        self._get_patient(pid)
        self.data.setdefault("preferences", [])
        pre = next((x for x in self.data["preferences"] if x["patient_id"]==pid), None)
        if not pre:
            pre = {"patient_id": pid, "diet": diet or "", "preferred_gender": gender or "", "visiting_hours": visiting_hours or "", "viewed_by": [], "created_by": actor or staff_reader or "system", "created_at": now_iso(), "updated_at": None}
            self.data["preferences"].append(pre)
        else:
            if diet is not None: pre["diet"] = diet
            if gender is not None: pre["preferred_gender"] = gender
            if visiting_hours is not None: pre["visiting_hours"] = visiting_hours
        if staff_reader:
            if staff_reader not in pre["viewed_by"]:
                pre["viewed_by"].append(staff_reader)
        pre["updated_at"] = now_iso()
        if actor: pre["updated_by"] = actor
        self.repo.save(self.data)

    def get_preferences(self, pid:str):
        return next((x for x in self.data.get("preferences", []) if x["patient_id"]==pid), None)

    # ---------- handover ----------
    def create_or_update_handover(self, username:str, pid:str, text:str) -> str:
        self._ensure_can_write(username)
        if not self.can_access(username, pid):
            raise PermissionError("no access to patient")
        self.data.setdefault("handover_notes", [])
        now = now_iso()
        h = next((x for x in self.data["handover_notes"] if x["patient_id"]==pid), None)
        if not h:
            hid = self._new_id("handover","H")
            self.data["handover_notes"].append({
                "id": hid, "patient_id": pid, "text": text or "",
                "created_by": username, "created_at": now, "updated_at": None
            })
            self._audit(username, "create_handover", {"patient_id": pid, "id": hid})
            self.repo.save(self.data)
            return hid
        else:
            h["text"] = text or ""
            h["updated_at"] = now
            self._audit(username, "update_handover", {"patient_id": pid, "id": h["id"]})
            self.repo.save(self.data)
            return h["id"]

    def get_handover(self, pid:str):
        return next((x for x in self.data.get("handover_notes", []) if x["patient_id"]==pid), None)

    # ---------- search & report (legacy structured search for UI) ----------
    def _within_date(self, ts_iso:str, start:Optional[str], end:Optional[str]) -> bool:
        ts = datetime.fromisoformat(ts_iso)
        if start:
            s = datetime.fromisoformat(start + "T00:00:00+00:00") if len(start)==10 else datetime.fromisoformat(start)
            if ts < s: return False
        if end:
            e = datetime.fromisoformat(end + "T23:59:59+00:00") if len(end)==10 else datetime.fromisoformat(end)
            if ts > e: return False
        return True

    def search_logs(self, kw:Optional[str], creator:Optional[str], start:Optional[str], end:Optional[str], types:Optional[List[str]], username:Optional[str]=None):
        kw_low = (kw or "").lower()
        types = types or ["observation","story"]
        out = []

        allowed_pids = None
        role = self._role(username) if username else None
        if username and role not in ("Admin","Auditor"):
            # Limit to patients assigned to the user while allowing additional record types in searches
            allowed_pids = set(self.get_assigned_patient_ids(username))
            allowed_types = {"observation","story","handover","preference","preferences","visit","visits"}
            types = [t for t in types if t in allowed_types]

        def high(text):
            if not kw_low: return text
            return re.sub(re.escape(kw_low), lambda m: f"**{m.group(0)}**", text, flags=re.IGNORECASE)

        if "observation" in types:
            for o in self.data.get("observations", []):
                if o.get("deleted"): continue
                if allowed_pids is not None and o["patient_id"] not in allowed_pids: continue
                if creator and o["created_by"] != creator: continue
                if not self._within_date(o["created_at"], start, end): continue
                blob = f'{o["note"]} pain={o["pain"]} appetite={o["appetite"]}'
                if kw_low and kw_low not in blob.lower(): 
                    continue
                out.append({"type":"observation", **o, "highlight": high(blob)})
        if "story" in types:
            for s in self.data.get("stories", []):
                if s.get("deleted"): continue
                if allowed_pids is not None and s["patient_id"] not in allowed_pids: continue
                if creator and s["created_by"] != creator: continue
                if not self._within_date(s["created_at"], start, end): continue
                if kw_low and kw_low not in (s["text"] or "").lower(): 
                    continue
                out.append({"type":"story", **s, "highlight": high(s["text"] or "")})
        if "handover" in types:
            for h in self.data.get("handover_notes", []):
                if allowed_pids is not None and h["patient_id"] not in allowed_pids: continue
                if creator and h.get("created_by") != creator and h.get("updated_by") != creator: continue
                when = h.get("updated_at") or h.get("created_at")
                if when and not self._within_date(when, start, end): continue
                blob = (h.get("text") or "")
                if kw_low and kw_low not in blob.lower(): continue
                out.append({"type":"handover", **h, "highlight": high(blob)})
        if "preference" in types or "preferences" in types:
            for p in self.data.get("preferences", []):
                if allowed_pids is not None and p["patient_id"] not in allowed_pids: continue
                if creator and p.get("created_by") != creator and p.get("updated_by") != creator: continue
                when = p.get("updated_at") or p.get("created_at")
                if (start or end) and when and not self._within_date(when, start, end): 
                    continue
                blob = f'diet={p.get("diet","")} gender={p.get("preferred_gender","")} visiting_hours={p.get("visiting_hours","")}'
                if kw_low and kw_low not in blob.lower(): continue
                out.append({"type":"preference", **p, "highlight": high(blob)})
        if "visit" in types or "visits" in types:
            for v in self.data.get("visits", []):
                if allowed_pids is not None and v["patient_id"] not in allowed_pids: continue
                if creator and v.get("created_by") != creator: continue
                when = v.get("start") or v.get("created_at")
                if when and not self._within_date(when, start, end): continue
                blob = f'start={v.get("start","")} end={v.get("end","")}'
                if kw_low and kw_low not in blob.lower(): continue
                out.append({"type":"visit", **v, "highlight": high(blob)})
        if "audit" in types:
            for a in self.data.get("audit", []):
                if creator and a["actor"] != creator: continue
                if not self._within_date(a["ts"], start, end): continue
                blob = f'{a["action"]} {a.get("meta")}'
                if kw_low and kw_low not in blob.lower(): 
                    continue
                out.append({"type":"audit", **a, "highlight": high(blob)})
        out.sort(key=lambda x: (x.get("created_at") or x.get("ts")), reverse=True)
        return out

    # ===== NEW: generic search iterator API (observations/stories/visits/preferences/handover_notes) =====
    def _parse_ts(self, val: Optional[str]) -> datetime:
        """Robust ISO parser → timezone-aware datetime; fallback to epoch if missing/invalid."""
        if not val:
            return datetime(1970,1,1, tzinfo=timezone.utc)
        try:
            dt = datetime.fromisoformat(val)
            # If naive, assume UTC to keep ordering stable
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime(1970,1,1, tzinfo=timezone.utc)

    def _match(self, rec: dict, keyword: str) -> bool:
        kw = (keyword or "").strip().lower()
        if not kw:
            return True
        text = (rec.get("text") or "")
        return kw in text.lower()

    def _iter_records(self, kinds: Tuple[str, ...], start_dt: Optional[datetime], end_dt: Optional[datetime]):
        """
        统一把不同 kind 的记录转成标准结构：
        {type, id, patient_id, ts(datetime), text(str), meta(dict)}
        """
        data = self.data  # Use in-memory data; if disk must be authoritative, switch to self.repo.load()
        for kind in kinds:
            bucket = data.get(kind, [])
            if not isinstance(bucket, list):
                continue
            for it in bucket:
                # observations
                if kind == "observations":
                    ts = self._parse_ts(it.get("created_at") or it.get("ts"))
                    if (start_dt and ts < start_dt) or (end_dt and ts > end_dt): continue
                    txt = " ".join(filter(None, [
                        f"pain={it.get('pain')}",
                        f"appetite={it.get('appetite')}",
                        it.get("note"),
                        it.get("created_by"),
                    ]))
                    yield {"type": "observations", "id": it.get("id"), "patient_id": it.get("patient_id"),
                           "ts": ts, "text": txt, "meta": it}

                # stories
                elif kind == "stories":
                    ts = self._parse_ts(it.get("created_at") or it.get("ts"))
                    if (start_dt and ts < start_dt) or (end_dt and ts > end_dt): continue
                    txt = it.get("text") or ""
                    yield {"type": "stories", "id": it.get("id"), "patient_id": it.get("patient_id"),
                           "ts": ts, "text": txt, "meta": it}

                # visits
                elif kind == "visits":
                    ts = self._parse_ts(it.get("start") or it.get("created_at") or it.get("ts"))
                    if (start_dt and ts < start_dt) or (end_dt and ts > end_dt): continue
                    txt = " ".join(filter(None, [
                        f"start={it.get('start')}",
                        f"end={it.get('end')}",
                        it.get("location"),
                        it.get("doctor"),
                        it.get("created_by"),
                    ]))
                    yield {"type": "visits", "id": it.get("id"), "patient_id": it.get("patient_id"),
                           "ts": ts, "text": txt, "meta": it}

                # preferences
                elif kind == "preferences":
                    ts = self._parse_ts(it.get("updated_at") or it.get("created_at") or it.get("ts"))
                    if (start_dt and ts < start_dt) or (end_dt and ts > end_dt): continue
                    txt = " ".join(filter(None, [
                        f"diet={it.get('diet','')}",
                        f"gender={it.get('preferred_gender','')}",
                        f"visiting_hours={it.get('visiting_hours','')}",
                        it.get("note"),
                    ]))
                    yield {"type": "preferences", "id": it.get("id"), "patient_id": it.get("patient_id"),
                           "ts": ts, "text": txt, "meta": it}

                # handover notes
                elif kind == "handover_notes":
                    ts = self._parse_ts(it.get("updated_at") or it.get("created_at") or it.get("ts"))
                    if (start_dt and ts < start_dt) or (end_dt and ts > end_dt): continue
                    txt = it.get("text") or ""
                    yield {"type": "handover", "id": it.get("id"), "patient_id": it.get("patient_id"),
                           "ts": ts, "text": txt, "meta": it}

    def search_entries(
        self,
        keyword: str = "",
        start: Optional[str] = None,
        end: Optional[str] = None,
        types: Optional[Set[str]] = None,
    ) -> List[dict]:
        """
        在 observations/stories/visits/preferences/handover_notes 中按关键词与日期范围搜索。
        返回统一列表：[{type, id, patient_id, ts, text, meta}, ...]；按 ts 升序。
        """
        # Configure the time window (string value accepting YYYY-MM-DD or full ISO)
        start_dt = None
        end_dt = None
        try:
            if start:
                start_dt = datetime.fromisoformat(start + "T00:00:00+00:00") if len(start) == 10 else datetime.fromisoformat(start)
            if end:
                end_dt = datetime.fromisoformat(end + "T23:59:59+00:00") if len(end) == 10 else datetime.fromisoformat(end)
        except Exception:
            # Graceful handling: treat invalid dates as no range restriction
            start_dt = None
            end_dt = None

        incoming = set(types or self.SEARCHABLE_TYPES)
        mapped = set("handover_notes" if k == "handover" else k for k in incoming)
        tset = mapped & self.SEARCHABLE_TYPES
        results: List[dict] = []
        # iterate over each record bucket (handover uses handover_notes)
        kinds: Tuple[str, ...] = tuple(sorted(tset, key=lambda x: x))

        for rec in self._iter_records(kinds, start_dt, end_dt):
            if self._match(rec, keyword):
                results.append(rec)

        return sorted(results, key=lambda r: r["ts"])

    def export_csv(self, rows:list[dict]) -> str:
        if not rows: return ""
        f = io.StringIO()
        cols = sorted({k for r in rows for k in r.keys()})
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
        return f.getvalue()

    def monthly_audit_view(self, year:int, month:int):
        out = []
        for o in self.data.get("observations", []):
            if o.get("deleted"): continue
            dt = datetime.fromisoformat(o["created_at"])
            if dt.year==year and dt.month==month:
                out.append({"type":"observation", **o})
        for s in self.data.get("stories", []):
            dt = datetime.fromisoformat(s["created_at"])
            if dt.year==year and dt.month==month:
                out.append({"type":"story", **s})
        for a in self.data.get("audit", []):
            dt = datetime.fromisoformat(a["ts"])
            if dt.year==year and dt.month==month:
                out.append({"type":"audit", **a})
        out.sort(key=lambda x: (x.get("created_at") or x.get("ts")), reverse=True)
        return out

    def text_report(self, patient_id:Optional[str]=None, date_iso:Optional[str]=None, date_from:Optional[str]=None, date_to:Optional[str]=None) -> str:
        lines = []
        if patient_id:
            lines.append(f"# Report for patient {patient_id}")
            for o in sorted([x for x in self.data.get("observations", []) if x["patient_id"]==patient_id and not x.get("deleted") and (not date_from and not date_to or self._within_date(x["created_at"], date_from, date_to))], key=lambda x: x["created_at"]):
                lines.append(f'- [{o["created_at"]}] Observation by {o["created_by"]}: pain={o["pain"]} appetite={o["appetite"]} note={o["note"]}')
            stories = [
                x for x in self.data.get("stories", [])
                if x["patient_id"]==patient_id and (not date_from and not date_to or self._within_date(x["created_at"], date_from, date_to))
            ]
            for s in sorted(stories, key=lambda x: x["created_at"]):
                deleted_note = ""
                if s.get("deleted"):
                    deleted_at = s.get("deleted_at")
                    deleted_by = s.get("deleted_by")
                    meta_bits = []
                    if deleted_at:
                        meta_bits.append(f"at {deleted_at}")
                    if deleted_by:
                        meta_bits.append(f"by {deleted_by}")
                    info = " ".join(meta_bits)
                    deleted_note = f" [DELETED{(' ' + info) if info else ''}]"
                lines.append(f'- [{s["created_at"]}] Story by {s.get("created_by","Unknown")}{deleted_note}: {s.get("text","")}')
        elif date_iso:
            dt = datetime.fromisoformat(date_iso)
            y,m,d = dt.year, dt.month, dt.day
            lines.append(f"# Report for date {y:04d}-{m:02d}-{d:02d}")
            for o in self.data.get("observations", []):
                if o.get("deleted"): continue
                ts = datetime.fromisoformat(o["created_at"])
                if ts.date() == dt.date():
                    lines.append(f'- [Patient {o["patient_id"]}] Observation by {o["created_by"]}: pain={o["pain"]} appetite={o["appetite"]} note={o["note"]}')
            for s in self.data.get("stories", []):
                ts = datetime.fromisoformat(s["created_at"])
                if ts.date() == dt.date():
                    deleted_note = ""
                    if s.get("deleted"):
                        deleted_at = s.get("deleted_at")
                        deleted_by = s.get("deleted_by")
                        meta_bits = []
                        if deleted_at:
                            meta_bits.append(f"at {deleted_at}")
                        if deleted_by:
                            meta_bits.append(f"by {deleted_by}")
                        info = " ".join(meta_bits)
                        deleted_note = f" [DELETED{(' ' + info) if info else ''}]"
                    lines.append(f'- [Patient {s.get("patient_id","N/A")}] Story by {s.get("created_by","Unknown")}{deleted_note}: {s.get("text","")}')
        return "\n".join(lines)

    # ---------- backups ----------
    def list_backups(self):
        return self.repo.list_backups()

    def backup_now(self, actor:str) -> str:
        path = self.repo.backup()
        self._audit(actor, "backup", {"path": path})
        return path

    def restore_from_backup(self, actor:str, backup_filename:str):
        cand = [b for b in self.list_backups() if b.endswith(backup_filename)]
        if not cand:
            raise FileNotFoundError("backup not found")
        self.repo.restore(cand[0])
        self.data = self.repo.load()
        self._audit(actor, "restore", {"path": cand[0]})

    def checksum(self) -> str:
        return self.repo.checksum()

    def global_search(self, kw: str, include_deleted: bool = False, limit: int = 1000):
        """
        在整个数据仓库里做大小写不敏感的“包含式”搜索；忽略下方筛选，直接返回所有可能命中。
        返回统一结构的 rows: List[dict]
        """
        if not kw:
            return []

        kw_l = str(kw).strip().lower()
        data = self.data  # Current in-memory data; prefer self.repo.load() if disk should be authoritative

        rows = []

        def norm(x):
            try:
                return str(x).lower()
            except Exception:
                return ""

        def record_contains(obj):
            """递归判断任意值里是否包含 kw_l"""
            found = False
            def walk(o):
                nonlocal found
                if found:
                    return
                if isinstance(o, dict):
                    # Filter out soft-deleted entries
                    if not include_deleted and o.get("deleted") is True:
                        return
                    for k, v in o.items():
                        if kw_l in norm(k):  # Allow hits in key names (for example, patient_id)
                            found = True; return
                        if isinstance(v, (str, int, float)):
                            if kw_l in norm(v):
                                found = True; return
                        else:
                            walk(v)
                elif isinstance(o, list):
                    for item in o:
                        walk(item)
                else:
                    if isinstance(o, (str, int, float)) and kw_l in norm(o):
                        found = True
            walk(obj)
            return found

        def first_snippet(rec):
            """抓取首个命中的字段，做展示摘要"""
            for k, v in rec.items():
                if isinstance(v, (str, int, float)) and kw_l in norm(v):
                    return f"{k}={v}"
            # Recurse one additional level
            for k, v in rec.items():
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        if isinstance(vv, (str, int, float)) and kw_l in norm(vv):
                            return f"{k}.{kk}={vv}"
            return ""

        # Keys are derived from the project data model; skip any missing ones without raising errors
        buckets = [
            ("patient",       data.get("patients", [])),
            ("visit",         data.get("visits", [])),
            ("observation",   data.get("observations", [])),
            ("story",         data.get("stories", [])),
            ("handover",      data.get("handover_notes", [])),
            ("audit",         data.get("audit", [])),
            ("log",           data.get("logs", [])),
        ]

        for typ, items in buckets:
            if not isinstance(items, list):
                continue
            for idx, rec in enumerate(items):
                if not isinstance(rec, dict):
                    continue
                if not include_deleted and rec.get("deleted") is True:
                    continue
                if record_contains(rec):
                    # Extract shared fields when possible to support list rendering
                    row = {
                        "type": typ,
                        "patient_id": rec.get("patient_id") or rec.get("pid") or rec.get("patientId") or "",
                        "visit_id": rec.get("visit_id") or rec.get("vid") or "",
                        "author": rec.get("username") or rec.get("creator") or rec.get("author") or "",
                        "time": rec.get("timestamp") or rec.get("created_at") or rec.get("time") or rec.get("date") or rec.get("start") or "",
                        "id": rec.get("id") or "",
                        "snippet": first_snippet(rec),
                        "_path": f"{typ}[{idx}]",
                    }
                    rows.append(row)
                    if len(rows) >= limit:
                        return rows
        return rows



