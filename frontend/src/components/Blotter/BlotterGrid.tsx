import { useCallback, useEffect, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, CellValueChangedEvent, GetRowIdParams, RowClickedEvent } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

import { colors } from '../../theme/tokens';
import { useBlotterStore } from '../../stores/blotterStore';
import { usePricerStore } from '../../stores/pricerStore';
import type { BlotterOrder } from '../../types';

const ALL_COLUMNS: ColDef<BlotterOrder>[] = [
  { field: 'id', headerName: 'ID', width: 80, cellStyle: { fontSize: '11px', textAlign: 'left' } },
  {
    field: 'added_time', headerName: 'Time', width: 85,
    valueFormatter: (params) => {
      if (!params.value) return '';
      const parts = String(params.value).split('T');
      return parts[1] || params.value; // "HH:MM:SS" or legacy "HH:MM"
    },
  },
  { field: 'underlying', headerName: 'Underlying', width: 90 },
  { field: 'structure', headerName: 'Structure', width: 200, flex: 1 },
  {
    field: 'bid', headerName: 'Bid', width: 80,
    enableCellChangeFlash: true,
    cellStyle: (p) => {
      if (p.value === '--') return { color: colors.textStale, fontStyle: 'italic', textAlign: 'right' };
      return { color: colors.greenPrimary, fontStyle: 'normal', textAlign: 'right' };
    },
  },
  {
    field: 'mid', headerName: 'Mid', width: 80,
    enableCellChangeFlash: true,
    cellStyle: (p) => {
      if (p.value === '--') return { color: colors.textStale, fontStyle: 'italic', fontWeight: 400, textAlign: 'right' };
      return { color: colors.textPrimary, fontStyle: 'normal', fontWeight: 700, textAlign: 'right' };
    },
  },
  {
    field: 'offer', headerName: 'Offer', width: 80,
    enableCellChangeFlash: true,
    cellStyle: (p) => {
      if (p.value === '--') return { color: colors.textStale, fontStyle: 'italic', textAlign: 'right' };
      return { color: colors.redPrimary, fontStyle: 'normal', textAlign: 'right' };
    },
  },
  { field: 'bid_size', headerName: 'Bid Size', width: 80, cellStyle: { textAlign: 'right' } },
  { field: 'offer_size', headerName: 'Offer Size', width: 85, cellStyle: { textAlign: 'right' } },
  {
    field: 'side', headerName: 'Bid/Offered', width: 100, editable: true,
    cellEditor: 'agSelectCellEditor',
    cellEditorParams: { values: ['', 'Bid', 'Offered'] },
    cellStyle: (p) => ({
      backgroundColor: colors.bgEditable,
      color: p.value === 'Bid' ? colors.greenPrimary : p.value === 'Offered' ? colors.redPrimary : colors.textPrimary,
      fontWeight: p.value ? 700 : 400,
      textAlign: 'center',
    }),
  },
  {
    field: 'size', headerName: 'Size', width: 70, editable: true,
    cellStyle: { backgroundColor: colors.bgEditable, textAlign: 'right' },
  },
  {
    field: 'traded', headerName: 'Traded', width: 80, editable: true,
    cellEditor: 'agSelectCellEditor',
    cellEditorParams: { values: ['No', 'Yes'] },
    cellStyle: { backgroundColor: colors.bgEditable, textAlign: 'center' },
  },
  {
    field: 'bought_sold', headerName: 'Bought/Sold', width: 100, editable: true,
    cellEditor: 'agSelectCellEditor',
    cellEditorParams: { values: ['', 'Bought', 'Sold'] },
    cellStyle: (p) => ({
      backgroundColor: colors.bgEditable,
      color: p.value === 'Bought' ? colors.greenPrimary : p.value === 'Sold' ? colors.redPrimary : colors.textPrimary,
      fontWeight: p.value ? 700 : 400,
      textAlign: 'center',
    }),
  },
  {
    field: 'traded_price', headerName: 'Traded Px', width: 85, editable: true,
    cellStyle: { backgroundColor: colors.bgEditable, textAlign: 'right' },
  },
  {
    field: 'initiator', headerName: 'Initiator', width: 90, editable: true,
    cellStyle: { backgroundColor: colors.bgEditable },
  },
  {
    field: 'pnl', headerName: 'PnL', width: 90,
    enableCellChangeFlash: true,
    cellStyle: (p) => {
      const v = String(p.value || '');
      if (v.startsWith('-')) return { color: colors.redPrimary, fontWeight: 700, textAlign: 'right' };
      if (v.startsWith('+')) return { color: colors.greenPrimary, fontWeight: 700, textAlign: 'right' };
      return { color: colors.textPrimary, fontWeight: 400, textAlign: 'right' };
    },
  },
];

export default function BlotterGrid() {
  const { orders, visibleColumns, loadOrders, updateOrderField } = useBlotterStore();

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  const columnDefs = useMemo(
    () => ALL_COLUMNS.filter((c) => visibleColumns.includes(c.field as string)),
    [visibleColumns],
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      resizable: true,
      sortable: true,
      suppressMovable: true,
    }),
    [],
  );

  const getRowId = useCallback((params: GetRowIdParams<BlotterOrder>) => params.data.id, []);

  const onCellValueChanged = useCallback(
    (event: CellValueChangedEvent<BlotterOrder>) => {
      if (event.data && event.colDef.field) {
        updateOrderField(event.data.id, event.colDef.field, String(event.newValue ?? ''));
      }
    },
    [updateOrderField],
  );

  const onRowClicked = useCallback((event: RowClickedEvent<BlotterOrder>) => {
    if (event.data?._table_data) {
      usePricerStore.getState().recallOrder(event.data);
    }
  }, []);

  return (
    <div
      className="ag-theme-alpine-dark"
      style={{ width: '100%', height: Math.max(200, Math.min(orders.length * 42 + 56, 600)) }}
    >
      <AgGridReact<BlotterOrder>
        rowData={orders}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        getRowId={getRowId}
        onCellValueChanged={onCellValueChanged}
        onRowClicked={onRowClicked}
        singleClickEdit
        stopEditingWhenCellsLoseFocus
        rowSelection="multiple"
        animateRows
      />
    </div>
  );
}
