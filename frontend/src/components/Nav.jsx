import { NavLink } from "react-router-dom";
import { CalendarCheck, History, MessageSquare, User } from "lucide-react";
import "./Nav.css";

const LINKS = [
  { to: "/today", label: "Today", Icon: CalendarCheck },
  { to: "/chat", label: "Chat", Icon: MessageSquare },
  { to: "/history", label: "History", Icon: History },
  { to: "/profile", label: "Profile", Icon: User },
];

export default function Nav() {
  return (
    <nav className="nav" aria-label="Main">
      {LINKS.map(({ to, label, Icon }) => (
        <NavLink key={to} to={to} className="nav-link">
          <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
