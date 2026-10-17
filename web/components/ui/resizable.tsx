"use client";
// shadcn/ui Resizable pattern (MIT), referenced via 21st.dev. See SOURCES.md.
import * as Panels from "react-resizable-panels";
export const ResizablePanel = Panels.Panel;
export function ResizablePanelGroup(
  props: React.ComponentProps<typeof Panels.PanelGroup>,
) {
  return (
    <Panels.PanelGroup
      {...props}
      className={"resizable-group " + (props.className ?? "")}
    />
  );
}
export function ResizableHandle() {
  return (
    <Panels.PanelResizeHandle
      className="resize-handle"
      aria-label="Resize workspace panels"
    >
      <span />
    </Panels.PanelResizeHandle>
  );
}
