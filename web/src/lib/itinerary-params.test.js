import { test, describe } from 'node:test'
import assert from 'node:assert/strict'

import { PARAM_DEFAULTS, isDefault, parseParams, toQuery } from './itinerary-params.js'

describe('parseParams：把 URL 参数还原成行程参数', () => {
  test('完整参数能解析', () => {
    const p = parseParams({ days: '3', budget: '400', pace: 'tight', seed: '7' })
    assert.deepEqual(p, { days: 3, budget: 400, pace: 'tight', seed: 7, restored: true })
  })

  test('query 是字符串也要能解析（URL 就是字符串）', () => {
    const p = parseParams({ days: '1', budget: '50', pace: 'relaxed', seed: '0' })
    assert.equal(p.days, 1)
    assert.equal(p.budget, 50)
    assert.equal(p.pace, 'relaxed')
    assert.equal(p.seed, 0)
    assert.equal(p.restored, true)
  })

  test('空参数 → 不恢复（不能假装恢复成功）', () => {
    for (const empty of [{}, { days: '' }, { days: undefined }, null]) {
      const p = parseParams(empty ?? {})
      assert.equal(p.restored, false, `输入 ${JSON.stringify(empty)} 不应恢复`)
      assert.equal(p.days, PARAM_DEFAULTS.days)
    }
  })

  test('天数越界会被夹紧', () => {
    assert.equal(parseParams({ days: '999' }).days, 30)
    assert.equal(parseParams({ days: '-5' }).days, 1)
    assert.equal(parseParams({ days: '2.9' }).days, 2)
  })

  test('非法预算/节奏退回默认值，但整体仍算恢复成功', () => {
    const p = parseParams({ days: '2', budget: '999', pace: 'chaos', seed: '1' })
    assert.equal(p.restored, true)
    assert.equal(p.budget, PARAM_DEFAULTS.budget)
    assert.equal(p.pace, PARAM_DEFAULTS.pace)
  })

  test('种子为负数或非数字时归零', () => {
    assert.equal(parseParams({ days: '2', seed: '-3' }).seed, 0)
    assert.equal(parseParams({ days: '2', seed: 'abc' }).seed, 0)
  })
})

describe('toQuery：参数写回 URL', () => {
  test('四个参数都写出来（链接要自解释）', () => {
    assert.deepEqual(toQuery({ days: 2, budget: 150, pace: 'normal', seed: 0 }), {
      days: '2',
      budget: '150',
      pace: 'normal',
      seed: '0',
    })
  })

  test('往返一致：toQuery → parseParams 得到原值', () => {
    const origin = { days: 4, budget: 50, pace: 'tight', seed: 11 }
    const back = parseParams(toQuery(origin))
    assert.deepEqual(back, { ...origin, restored: true })
  })

  test('天数越界时输出也会被夹紧', () => {
    assert.equal(toQuery({ days: 99, budget: 150, pace: 'normal', seed: 0 }).days, '30')
  })

  test('isDefault 能识别默认参数', () => {
    assert.equal(isDefault(PARAM_DEFAULTS), true)
    assert.equal(isDefault({ ...PARAM_DEFAULTS, seed: 1 }), false)
  })
})
