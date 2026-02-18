import { colors, fonts, fontSizes, spacing, radius } from '../../theme/tokens';
import { STRUCTURE_TYPE_OPTIONS } from '../../theme/tokens';
import { usePricerStore } from '../../stores/pricerStore';

const inputStyle: React.CSSProperties = {
  padding: spacing.md,
  backgroundColor: colors.bgElevated,
  color: colors.textPrimary,
  border: `1px solid ${colors.borderDefault}`,
  borderRadius: radius.md,
  fontFamily: fonts.mono,
  fontSize: fontSizes.md,
  outline: 'none',
};

const labelStyle: React.CSSProperties = {
  color: colors.textSecondary,
  fontSize: fontSizes.base,
  marginBottom: spacing.sm,
  fontWeight: 500,
  letterSpacing: '0.3px',
  textTransform: 'uppercase' as const,
};

function Field({
  label,
  children,
  width,
}: {
  label: string;
  children: React.ReactNode;
  width?: string;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width }}>
      <label style={labelStyle}>{label}</label>
      {children}
    </div>
  );
}

export default function PricerToolbar() {
  const store = usePricerStore();
  const { header } = store;

  // Only show toolbar after first price
  if (!header) return null;

  return (
    <div
      style={{
        backgroundColor: colors.bgSurface,
        padding: `15px ${spacing.xxl}`,
        borderRadius: radius.lg,
        marginTop: '15px',
        display: 'flex',
        gap: spacing.lg,
        alignItems: 'flex-end',
        flexWrap: 'wrap',
      }}
    >
      <Field label="Underlying" width="90px">
        <input
          value={store.underlying}
          onChange={(e) => {
            store.setToolbarField('underlying', e.target.value);
          }}
          onBlur={() => store.repriceFromTable()}
          style={inputStyle}
        />
      </Field>
      <Field label="Structure" width="150px">
        <select
          value={store.structureType}
          onChange={(e) => {
            store.applyTemplate(e.target.value);
          }}
          style={{ ...inputStyle, color: store.structureType ? colors.textPrimary : colors.textTertiary }}
        >
          <option value="">Custom</option>
          {STRUCTURE_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Tie" width="80px">
        <input
          type="number"
          value={store.stockRef}
          onChange={(e) => store.setToolbarField('stockRef', e.target.value)}
          onBlur={() => store.repriceFromTable()}
          style={inputStyle}
        />
      </Field>
      <Field label="Delta" width="70px">
        <input
          type="number"
          value={store.delta}
          onChange={(e) => store.setToolbarField('delta', e.target.value)}
          onBlur={() => store.repriceFromTable()}
          style={inputStyle}
        />
      </Field>
      <Field label="Broker Px" width="85px">
        <input
          type="number"
          value={store.brokerPrice}
          onChange={(e) => store.setToolbarField('brokerPrice', e.target.value)}
          onBlur={() => store.repriceFromTable()}
          style={inputStyle}
        />
      </Field>
      <Field label="Side" width="90px">
        <select
          value={store.quoteSide}
          onChange={(e) => {
            store.setToolbarField('quoteSide', e.target.value);
            store.repriceFromTable();
          }}
          style={inputStyle}
        >
          <option value="bid">Bid</option>
          <option value="offer">Offer</option>
        </select>
      </Field>
      <Field label="Qty" width="70px">
        <input
          type="number"
          value={store.quantity}
          onChange={(e) => store.setToolbarField('quantity', e.target.value)}
          onBlur={() => store.repriceFromTable()}
          style={inputStyle}
        />
      </Field>
    </div>
  );
}
