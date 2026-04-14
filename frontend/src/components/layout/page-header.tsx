import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";

interface PageHeaderProps {
  title: string;
  description: string;
  eyebrow?: string;
  badge?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, eyebrow, badge, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <div className="space-y-3">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="hero-title">{title}</h1>
          {badge ? <Badge variant="primary">{badge}</Badge> : null}
        </div>
        <p className="max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">{description}</p>
      </div>
      {actions ? <div className="flex items-center gap-3">{actions}</div> : null}
    </div>
  );
}
