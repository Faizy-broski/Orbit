/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import type { FormEvent } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { EUserPermissions, EUserPermissionsLevel, STATE_GROUPS } from "@plane/constants";
import { Button } from "@plane/propel/button";
import { PlusIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TStateGroups } from "@plane/types";
import { CustomSelect, Input } from "@plane/ui";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useUserPermissions } from "@/hooks/store/user";

const DEFAULT_GROUP: TStateGroups = "started";

export const KanbanAddStateColumn = observer(function KanbanAddStateColumn() {
  const { workspaceSlug, projectId } = useParams();
  const { allowPermissions } = useUserPermissions();
  const { createState } = useProjectState();
  const [isOpen, setIsOpen] = useState(false);
  const [name, setName] = useState("");
  const [group, setGroup] = useState<TStateGroups>(DEFAULT_GROUP);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!workspaceSlug || !projectId) return null;
  const isProjectAdmin = allowPermissions(
    [EUserPermissions.ADMIN],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug.toString(),
    projectId.toString()
  );
  if (!isProjectAdmin) return null;

  const close = () => {
    setIsOpen(false);
    setName("");
    setGroup(DEFAULT_GROUP);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await createState(workspaceSlug.toString(), projectId.toString(), {
        name: trimmedName,
        group,
        color: STATE_GROUPS[group].color,
      });
      close();
    } catch (error) {
      const { status } = (error ?? {}) as { status?: number };
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Could not add state",
        message: status === 400 ? "A state with that name already exists." : "Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen)
    return (
      <div className="flex-shrink-0 py-1">
        <button
          type="button"
          aria-label="Add state"
          title="Add state"
          className="flex size-8 items-center justify-center rounded-md border border-dashed border-strong text-secondary hover:bg-layer-1-hover"
          onClick={() => setIsOpen(true)}
        >
          <PlusIcon width={16} strokeWidth={2} />
        </button>
      </div>
    );

  return (
    <form
      className="flex h-fit w-[280px] flex-shrink-0 flex-col gap-2 rounded-md border border-subtle bg-surface-1 p-3"
      onSubmit={handleSubmit}
      onKeyDown={(event) => {
        if (event.key === "Escape") close();
      }}
    >
      <Input
        autoFocus
        aria-label="State name"
        placeholder="State name"
        maxLength={255}
        value={name}
        onChange={(event) => setName(event.target.value)}
        className="w-full"
      />
      <CustomSelect
        value={group}
        label={STATE_GROUPS[group].label}
        onChange={(value: TStateGroups) => setGroup(value)}
        input
      >
        {Object.values(STATE_GROUPS).map((stateGroup) => (
          <CustomSelect.Option key={stateGroup.key} value={stateGroup.key}>
            {stateGroup.label}
          </CustomSelect.Option>
        ))}
      </CustomSelect>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={close}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={!name.trim() || isSubmitting}>
          {isSubmitting ? "Adding" : "Add"}
        </Button>
      </div>
    </form>
  );
});
