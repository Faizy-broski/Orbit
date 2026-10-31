/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useUserPermissions } from "@/hooks/store/user";

type Props = {
  stateId: string;
  title: string;
  className: string;
  canRename: boolean;
};

export const KanbanColumnTitle = observer(function KanbanColumnTitle(props: Props) {
  const { stateId, title, className, canRename } = props;
  const { workspaceSlug, projectId } = useParams();
  const { allowPermissions } = useUserPermissions();
  const { updateState } = useProjectState();
  const [draft, setDraft] = useState<string | null>(null);
  // Escape unmounts the input, which can still fire blur; this stops that blur from saving.
  const isCancelled = useRef(false);

  const isProjectAdmin =
    !!workspaceSlug &&
    !!projectId &&
    allowPermissions(
      [EUserPermissions.ADMIN],
      EUserPermissionsLevel.PROJECT,
      workspaceSlug.toString(),
      projectId.toString()
    );

  if (!canRename || !isProjectAdmin) return <div className={className}>{title}</div>;

  const startEditing = () => {
    isCancelled.current = false;
    setDraft(title);
  };

  const save = async () => {
    if (isCancelled.current || draft === null) return;
    const name = draft.trim();
    setDraft(null);
    if (!name || name === title) return;
    try {
      await updateState(workspaceSlug.toString(), projectId.toString(), stateId, { name });
    } catch (error) {
      const { status } = (error ?? {}) as { status?: number };
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Could not rename state",
        message: status === 400 ? "A state with that name already exists." : "Please try again.",
      });
    }
  };

  if (draft === null)
    return (
      <button type="button" className={`${className} cursor-text text-left`} title="Rename" onClick={startEditing}>
        {title}
      </button>
    );

  return (
    <input
      autoFocus
      aria-label="State name"
      maxLength={255}
      value={draft}
      className="w-full min-w-0 rounded-sm border border-strong bg-surface-1 px-1 font-medium text-primary outline-none"
      onChange={(event) => setDraft(event.target.value)}
      onFocus={(event) => event.target.select()}
      onBlur={save}
      onKeyDown={(event) => {
        if (event.key === "Enter") event.currentTarget.blur();
        if (event.key === "Escape") {
          isCancelled.current = true;
          setDraft(null);
        }
      }}
    />
  );
});
