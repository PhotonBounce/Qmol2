import React, { useEffect, useState } from 'react'
import { CreditCard, Wallet, AlertCircle, ArrowUpRight, ArrowDownRight, Loader2 } from 'lucide-react'
import api from '../api/client'
import { useToast } from '../components/Toast'
import Skeleton from '../components/Skeleton'

export default function BillingPage() {
  const [balance, setBalance] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showAlert, setShowAlert] = useState(false)
  const [transactions, setTransactions] = useState([])
  const [txLoading, setTxLoading] = useState(false)
  const { addToast } = useToast()

  useEffect(() => {
    let isMounted = true
    const fetchBalance = async () => {
      setLoading(true)
      try {
        const res = await api.get('/billing/balance')
        if (isMounted) setBalance(res.data.credits_balance ?? 0)
      } catch (err) {
        if (isMounted) {
          setError(err.message)
          addToast(err.message, 'error')
        }
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    const fetchTransactions = async () => {
      setTxLoading(true)
      try {
        const res = await api.get('/billing/transactions')
        if (isMounted) setTransactions(res.data.items || [])
      } catch (err) {
        if (isMounted) {
          addToast('Transaction history is coming in V2.', 'info')
        }
      } finally {
        if (isMounted) setTxLoading(false)
      }
    }
    fetchBalance()
    fetchTransactions()
    return () => { isMounted = false }
  }, [addToast])

  const handleBuyCredits = () => {
    setShowAlert(true)
    addToast('Stripe integration is planned for V2. Credits are currently seeded manually.', 'info')
    setTimeout(() => setShowAlert(false), 3000)
  }

  const totalIn = transactions.filter((t) => t.type === 'credit').reduce((s, t) => s + t.amount, 0)
  const totalOut = transactions.filter((t) => t.type === 'debit').reduce((s, t) => s + t.amount, 0)

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Billing</h1>
        <p className="text-sm text-slate-500">Manage credits and view transaction history.</p>
      </div>

      {showAlert && (
        <div className="flex items-center gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Stripe integration is planned for V2. Credits are currently seeded manually.
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-3">
        <div className="card sm:col-span-2 flex flex-col justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Current Balance</p>
            {loading ? (
              <div className="mt-2">
                <Skeleton variant="card" />
              </div>
            ) : (
              <p className="mt-2 text-4xl font-bold text-slate-900">{balance.toFixed(2)} <span className="text-lg font-medium text-slate-500">credits</span></p>
            )}
          </div>
          <div className="mt-6 flex items-center gap-3">
            <button onClick={handleBuyCredits} className="btn-primary">
              <CreditCard className="mr-2 h-4 w-4" /> Buy Credits
            </button>
            <p className="text-xs text-slate-400">1 credit ≈ $0.01 USD</p>
          </div>
        </div>

        <div className="card space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
              <ArrowUpRight className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-xs text-slate-500">Total Purchased</p>
              <p className="text-lg font-semibold text-slate-900">{totalIn.toFixed(2)}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100">
              <ArrowDownRight className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-xs text-slate-500">Total Spent</p>
              <p className="text-lg font-semibold text-slate-900">{totalOut.toFixed(2)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Transaction History</h2>
        {txLoading ? (
          <div className="flex h-32 items-center justify-center text-sm text-slate-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading transactions…
          </div>
        ) : transactions.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-sm text-slate-400">
            Transaction history is coming in V2.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-4 py-3 font-semibold">Date</th>
                  <th className="px-4 py-3 font-semibold">Description</th>
                  <th className="px-4 py-3 font-semibold">Type</th>
                  <th className="px-4 py-3 font-semibold text-right">Amount</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {transactions.map((tx) => (
                  <tr key={tx.id}>
                    <td className="px-4 py-3 text-slate-700">{tx.created_at ? new Date(tx.created_at).toLocaleDateString() : '—'}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{tx.description}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ${
                        tx.type === 'credit_purchase' || tx.type === 'credit' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                      }`}>
                        {tx.type === 'credit_purchase' || tx.type === 'credit' ? 'Credit' : 'Debit'}
                      </span>
                    </td>
                    <td className={`px-4 py-3 text-right font-medium ${tx.type === 'credit_purchase' || tx.type === 'credit' ? 'text-green-600' : 'text-red-600'}`}>
                      {tx.type === 'credit_purchase' || tx.type === 'credit' ? '+' : '-'}{tx.amount.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex rounded-md bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">completed</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
