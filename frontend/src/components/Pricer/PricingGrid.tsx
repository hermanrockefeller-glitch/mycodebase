import { useCallback, useMemo, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, CellValueChangedEvent, GridReadyEvent, GetRowIdParams } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

import { colors } from '../../theme/tokens';
import { usePricerStore } from '../../stores/pricerStore';
import type { LegRow } from '../../types';

export default function PricingGrid() {
  const { tableData, tableError, repriceFromTable } = usePricerStore();
  const gridRef = useRef<AgGridReact<LegRow>>(null);

  // Separate leg rows from structure row
  const legRows = useMemo(() => tableData.filter((r) => r.leg !== 'Structure'), [tableData]);
  const structureRow = useMemo(() => {
    const row = tableData.find((r) => r.leg === 'Structure');
    return row ? [row] : [];
  }, [tableData]);

  const staleStyle = { color: colors.textStale, fontStyle: 'italic' as const };

  const columnDefs = useMemo<ColDef<LegRow>[]>(
    () => [
      { field: 'leg', headerName: 'Leg', editable: false, width: 75, pinned: 'left' as const },
      { field: 'expiry', headerName: 'Expiry', editable: true, width: 85,
        cellStyle: { backgroundColor: colors.bgEditable, textAlign: 'center' } },
      {
        field: 'strike', headerName: 'Strike', editable: true, width: 90,
        cellStyle: { backgroundColor: colors.bgEditable, textAlign: 'right' },
      },
      {
        field: 'type', headerName: 'Type', editable: true, width: 70,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: { values: ['C', 'P'] },
        cellStyle: { backgroundColor: colors.bgEditable, textAlign: 'center' },
      },
      {
        field: 'ratio', headerName: 'Ratio', editable: true, width: 70,
        cellStyle: { backgroundColor: colors.bgEditable, textAlign: 'center' },
        cellClassRules: {
          'ratio-buy': (p) => Number(p.value) > 0,
          'ratio-sell': (p) => Number(p.value) < 0,
        },
      },
      { field: 'bid_size', headerName: 'Bid Size', editable: false, width: 85,
        cellStyle: (p) => (p.value === '--' ? staleStyle : { textAlign: 'right' }) },
      {
        field: 'bid', headerName: 'Bid', editable: false, width: 85,
        cellStyle: (p) =>
          p.value === '--'
            ? staleStyle
            : { color: colors.greenPrimary, textAlign: 'right' },
      },
      {
        field: 'mid', headerName: 'Mid', editable: false, width: 85,
        cellStyle: (p) =>
          p.value === '--'
            ? staleStyle
            : { fontWeight: 700, textAlign: 'right' },
      },
      {
        field: 'offer', headerName: 'Offer', editable: false, width: 85,
        cellStyle: (p) =>
          p.value === '--'
            ? staleStyle
            : { color: colors.redPrimary, textAlign: 'right' },
      },
      { field: 'offer_size', headerName: 'Offer Size', editable: false, width: 95,
        cellStyle: (p) => (p.value === '--' ? staleStyle : { textAlign: 'right' }) },
    ],
    [],
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      resizable: true,
      suppressMovable: true,
    }),
    [],
  );

  const getRowId = useCallback((params: GetRowIdParams<LegRow>) => params.data.leg, []);

  const onCellValueChanged = useCallback(
    (_event: CellValueChangedEvent<LegRow>) => {
      // Sync grid edits back to store, then reprice
      const rows: LegRow[] = [];
      gridRef.current?.api?.forEachNode((node) => {
        if (node.data) rows.push(node.data);
      });
      // Also re-add structure row
      const structRow = usePricerStore.getState().tableData.find((r) => r.leg === 'Structure');
      if (structRow) rows.push(structRow);
      usePricerStore.setState({ tableData: rows });
      repriceFromTable();
    },
    [repriceFromTable],
  );

  const onGridReady = useCallback((_params: GridReadyEvent) => {
    // Auto-size on load
  }, []);

  return (
    <div>
      <div
        className="ag-theme-alpine-dark"
        style={{ width: '100%' }}
      >
        <AgGridReact<LegRow>
          ref={gridRef}
          rowData={legRows}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          getRowId={getRowId}
          pinnedBottomRowData={structureRow}
          onCellValueChanged={onCellValueChanged}
          onGridReady={onGridReady}
          singleClickEdit
          stopEditingWhenCellsLoseFocus
          domLayout="autoHeight"
        />
      </div>
      {tableError && (
        <div
          style={{
            color: colors.redPrimary,
            fontSize: '13px',
            marginTop: '8px',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {tableError}
        </div>
      )}
    </div>
  );
}
