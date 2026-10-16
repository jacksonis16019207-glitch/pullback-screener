// 投資資金から、その価格で何株（何単元）買えるかを計算する。

// 単元株数はJPXの銘柄一覧に含まれていないため、当面は100株として扱う。
export const DEFAULT_LOT_SIZE = 100

export type Affordability = {
  lots: number // 買える単元数
  shares: number // 1株単位（S株）で買える株数
  lotCost: number // 1単元の購入額
}

export function calcAffordability(
  funds: number,
  price: number,
  lotSize: number = DEFAULT_LOT_SIZE,
): Affordability {
  const lotCost = price * lotSize
  if (!(funds > 0) || !(price > 0)) {
    return { lots: 0, shares: 0, lotCost }
  }
  return {
    lots: Math.floor(funds / lotCost),
    shares: Math.floor(funds / price),
    lotCost,
  }
}
