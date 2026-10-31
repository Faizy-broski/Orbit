/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { ArrowLeft, ArrowRight, Trash2 } from "lucide-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { CustomMenu } from "@plane/ui";
import { getCurrentStateSequence } from "@plane/utils";
import { StateDeleteModal } from "@/components/project-states";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useUserPermissions } from "@/hooks/store/user";

type Props = {
  stateId: string;
};

export const KanbanStateColumnMenu = observer(function KanbanStateColumnMenu({ stateId }: Props) {
  const { workspaceSlug, projectId } = useParams();
  const { allowPermissions } = useUserPermissions();
  const { getProjectStates, moveStatePosition } = useProjectState();
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  if (!workspaceSlug || !projectId) return null;
  const isProjectAdmin = allowPermissions(
    [EUserPermissions.ADMIN],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug.toString(),
    projectId.toString()
  );
  const projectStates = getProjectStates(projectId.toString());
  const state = projectStates?.find((projectState) => projectState.id === stateId);
  if (!isProjectAdmin || !projectStates || !state) return null;

  // Board order is sequence alone, so a column can pass other groups while keeping its own group.
  const boardStates = [...projectStates].sort((a, b) => a.sequence - b.sequence);
  const position = boardStates.findIndex((boardState) => boardState.id === stateId);
  const previous = boardStates[position - 1];
  const next = boardStates[position + 1];
  const canDelete = !state.default && projectStates.length > 1;

  const move = (neighbourId: string, edge: "top" | "bottom") => {
    const sequence = getCurrentStateSequence(boardStates, { groupKey: state.group, id: neighbourId }, edge);
    moveStatePosition(workspaceSlug.toString(), projectId.toString(), stateId, { sequence });
  };

  return (
    <>
      <StateDeleteModal isOpen={isDeleteOpen} onClose={() => setIsDeleteOpen(false)} data={state} />
      <CustomMenu ellipsis placement="bottom-end" closeOnSelect>
        <CustomMenu.MenuItem disabled={!previous} onClick={() => previous && move(previous.id, "top")}>
          <span className="flex items-center gap-2">
            <ArrowLeft className="size-3.5" />
            Move column left
          </span>
        </CustomMenu.MenuItem>
        <CustomMenu.MenuItem disabled={!next} onClick={() => next && move(next.id, "bottom")}>
          <span className="flex items-center gap-2">
            <ArrowRight className="size-3.5" />
            Move column right
          </span>
        </CustomMenu.MenuItem>
        <CustomMenu.MenuItem disabled={!canDelete} onClick={() => canDelete && setIsDeleteOpen(true)}>
          <span className={`flex items-center gap-2 ${canDelete ? "text-danger-primary" : ""}`}>
            <Trash2 className="size-3.5" />
            {state.default ? "Default state can't be deleted" : "Delete state"}
          </span>
        </CustomMenu.MenuItem>
      </CustomMenu>
    </>
  );
});
