"use client"

import type React from "react"

import { useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import Navigation from "@/components/Navigation"

import {
  Phone,
  TrendingUp,
  Upload,
  FileText,
  Users,
  Clock,
  Trash2,
  RefreshCw,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  X,
  Plus,
} from "lucide-react"

// ===== Types mapped to your backend responses =====
// (kept minimal & defensive to avoid tight coupling)

type KnowledgeCollection = {
  id: string
  name: string
  description?: string | null
  is_public?: boolean
}

type KnowledgeDocument = {
  id: string
  title?: string | null
  file_name?: string | null
  file_url?: string | null
  status: string // "processing" | "ready" | "failed" | ...
  created_at?: string | null
  collections?: KnowledgeCollection[]
}

type DocumentUploadResponse = {
  document_id: string
  file_url?: string
  status: string
  message?: string
}

import { supabase } from "@/lib/supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? ""; // "" if using next.config rewrites

async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}


// ===== Simple helper to call JSON endpoints with cookies =====
async function apiJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getAccessToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      if (j?.detail) message = j.detail;
    } catch {}
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

async function uploadFileWithProgress(
  file: File,
  fields: { title: string; description?: string; collection_ids?: string },
  onProgress?: (pct: number) => void,
): Promise<DocumentUploadResponse> {
  const token = await getAccessToken();

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/knowledge/documents/upload`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (evt) => {
      if (evt.lengthComputable && onProgress) {
        onProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as DocumentUploadResponse);
        } catch {
          reject(new Error("Invalid JSON response from server"));
        }
      } else {
        try {
          const j = JSON.parse(xhr.responseText);
          reject(new Error(j?.detail || `${xhr.status} ${xhr.statusText}`));
        } catch {
          reject(new Error(`${xhr.status} ${xhr.statusText}`));
        }
      }
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));

    const form = new FormData();
    form.append("file", file);
    form.append("title", fields.title);
    if (fields.description) form.append("description", fields.description);
    if (fields.collection_ids) form.append("collection_ids", fields.collection_ids);

    xhr.send(form);
  });
}

// ===== Page Component =====
export default function DashboardPage() {
  const router = useRouter()

  // Existing demo/placeholder data
  const ongoingCalls = [
    { id: 1, customer: "John Smith", duration: "5:23", status: "active", sentiment: "positive" },
    { id: 2, customer: "Sarah Johnson", duration: "2:45", status: "active", sentiment: "neutral" },
    { id: 3, customer: "Mike Davis", duration: "8:12", status: "active", sentiment: "positive" },
  ]

  // ===== Knowledge Base state =====
  const [collections, setCollections] = useState<KnowledgeCollection[]>([])
  const [selectedCollectionIds, setSelectedCollectionIds] = useState<string[]>([])

  const [files, setFiles] = useState<
    {
      file: File
      title: string
      description: string
      progress: number
      status: "queued" | "uploading" | "processing" | "done" | "error"
      documentId?: string
      error?: string
    }[]
  >([])

  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [uploading, setUploading] = useState(false)

  // Create-collection inline form
  const [newColOpen, setNewColOpen] = useState(false)
  const [newColName, setNewColName] = useState("")
  const [newColDesc, setNewColDesc] = useState("")
  const [newColPublic, setNewColPublic] = useState(true)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  // Drag-and-drop visual
  const [isDragging, setIsDragging] = useState(false)

  // ===== Effects =====
  useEffect(() => {
    refreshCollections()
    refreshDocuments()
    // Poll for status updates if any processing documents exist
    const id = setInterval(async () => {
      const hasProcessing = documents.some((d) => d.status?.toLowerCase() === "processing")
      const hasUploading = files.some((f) => f.status === "uploading" || f.status === "processing")
      if (hasProcessing || hasUploading) {
        // Get fresh documents data
        const freshDocuments = await apiJSON<KnowledgeDocument[]>("/api/knowledge/documents?limit=50&offset=0")
        setDocuments(freshDocuments)
        
        // Update file status when documents finish processing
        setFiles((prevFiles) => {
          return prevFiles.map((file) => {
            if (file.status === "processing" && file.documentId) {
              // Find the corresponding document in fresh data
              const doc = freshDocuments.find((d) => d.id === file.documentId)
              if (doc && doc.status?.toLowerCase() === "ready") {
                return { ...file, status: "done" as const }
              }
            }
            return file
          })
        })
      }
    }, 5000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function refreshCollections() {
    try {
      const data = await apiJSON<KnowledgeCollection[]>(
        "/api/knowledge/collections?include_public=true&limit=200&offset=0",
      )
      setCollections(data)
    } catch (e: any) {
      console.error("Failed to load collections:", e?.message)
    }
  }

  async function refreshDocuments() {
    setLoadingDocs(true)
    try {
      const data = await apiJSON<KnowledgeDocument[]>("/api/knowledge/documents?limit=50&offset=0")
      setDocuments(data)
    } catch (e: any) {
      console.error("Failed to load documents:", e?.message)
    } finally {
      setLoadingDocs(false)
    }
  }

  // ===== Handlers: file selection/drag-drop =====
  function onPickFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const list = e.target.files ? Array.from(e.target.files) : []
    if (!list.length) return
    setFiles((prev) => [
      ...prev,
      ...list.map((f) => ({
        file: f,
        title: deriveTitleFromFile(f.name),
        description: "",
        progress: 0,
        status: "queued" as const,
      })),
    ])
    // clear input so the same file can be selected again if needed
    e.currentTarget.value = ""
  }

  function deriveTitleFromFile(name: string) {
    const dot = name.lastIndexOf(".")
    return dot > 0 ? name.slice(0, dot) : name
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    const list = e.dataTransfer?.files ? Array.from(e.dataTransfer.files) : []
    if (!list.length) return
    setFiles((prev) => [
      ...prev,
      ...list.map((f) => ({
        file: f,
        title: deriveTitleFromFile(f.name),
        description: "",
        progress: 0,
        status: "queued" as const,
      })),
    ])
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(true)
  }

  function onDragLeave() {
    setIsDragging(false)
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }

  // ===== Upload =====
  async function uploadAll() {
    if (!files.length) return
    setUploading(true)

    for (let i = 0; i < files.length; i++) {
      // skip already finished
      if (files[i].status === "done" || files[i].status === "processing") continue

      setFiles((prev) => {
        const copy = [...prev]
        copy[i] = { ...copy[i], status: "uploading", progress: 1, error: undefined }
        return copy
      })

      try {
        const resp = await uploadFileWithProgress(
          files[i].file,
          {
            title: files[i].title || deriveTitleFromFile(files[i].file.name),
            description: files[i].description || undefined,
            collection_ids: selectedCollectionIds.length ? JSON.stringify(selectedCollectionIds) : undefined,
          },
          (pct) => {
            setFiles((prev) => {
              const copy = [...prev]
              copy[i] = { ...copy[i], progress: pct }
              return copy
            })
          },
        )

        // Server returns status "processing" initially
        setFiles((prev) => {
          const copy = [...prev]
          copy[i] = {
            ...copy[i],
            status: resp.status?.toLowerCase() === "processing" ? "processing" : "done",
            documentId: resp.document_id,
            progress: 100,
          }
          return copy
        })
      } catch (e: any) {
        setFiles((prev) => {
          const copy = [...prev]
          copy[i] = { ...copy[i], status: "error", error: e?.message || "Upload failed" }
          return copy
        })
      }
    }

    await refreshDocuments()
    setUploading(false)
  }

  async function deleteDocument(id: string) {
    const ok = confirm("Delete this document?");
    if (!ok) return;
    try {
      const token = await getAccessToken();
      const res = await fetch(`${API_BASE}/api/knowledge/documents/${id}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        let msg = `${res.status} ${res.statusText}`;
        try {
          const j = await res.json();
          if (j?.detail) msg = j.detail;
        } catch {}
        throw new Error(msg);
      }
      await refreshDocuments();
    } catch (e: any) {
      alert(`Failed to delete: ${e?.message}`);
    }
  }
  

  async function createCollection() {
    if (!newColName.trim()) return
    try {
      const col = await apiJSON<KnowledgeCollection>("/api/knowledge/collections", {
        method: "POST",
        body: JSON.stringify({
          name: newColName.trim(),
          description: newColDesc || null,
          is_public: newColPublic,
        }),
      })
      setCollections((prev) => [col, ...prev])
      setNewColName("")
      setNewColDesc("")
      setNewColPublic(true)
      setNewColOpen(false)
    } catch (e: any) {
      alert(`Failed to create collection: ${e?.message}`)
    }
  }

  const selectedCollections = useMemo(
    () => collections.filter((c) => selectedCollectionIds.includes(c.id)),
    [collections, selectedCollectionIds],
  )

  return (
    <div className="min-h-screen bg-background">
      <Navigation variant="dashboard" />

      <main className="container mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Monitor your AI voice assistant performance</p>
        </div>

        {/* ===== Stats Cards ===== */}
        <div className="mb-8 grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Calls Attended</CardTitle>
              <Phone className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">1,284</div>
              <p className="text-xs text-muted-foreground">
                <span className="text-green-500">+12.5%</span> from last month
              </p>
              <Progress value={65} className="mt-3" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Ongoing Calls</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{ongoingCalls.length}</div>
              <p className="text-xs text-muted-foreground">Active conversations right now</p>
              <div className="mt-3 flex gap-2">
                {ongoingCalls.map((call) => (
                  <div key={call.id} className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Avg. Response Time
              </CardTitle>
              <CardDescription>Real-time monitoring of active conversations</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">1.2s</div>
              <p className="text-xs text-muted-foreground">
                <span className="text-green-500">-0.3s</span> faster than average
              </p>
              <Progress value={85} className="mt-3" />
            </CardContent>
          </Card>
        </div>

        {/* ===== 2-col layout ===== */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* ===== Knowledge Base (fully wired) ===== */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Knowledge Base
              </CardTitle>
              <CardDescription>Upload documents to train your AI assistant</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Collections picker */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Attach to Collections</Label>
                <div className="flex flex-wrap gap-2">
                  {collections.map((col) => {
                    const active = selectedCollectionIds.includes(col.id)
                    return (
                      <button
                        key={col.id}
                        type="button"
                        onClick={() =>
                          setSelectedCollectionIds((prev) =>
                            prev.includes(col.id) ? prev.filter((x) => x !== col.id) : [...prev, col.id],
                          )
                        }
                        className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                          active ? "border-primary bg-primary text-primary-foreground" : "border-border hover:bg-accent"
                        }`}
                        title={col.description || undefined}
                      >
                        {col.name}
                      </button>
                    )
                  })}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setNewColOpen((v) => !v)}
                    className="h-8 gap-1"
                  >
                    <Plus className="h-3.5 w-3.5" /> New Collection
                  </Button>
                </div>
                {selectedCollections.length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {selectedCollections.map((c) => (
                      <Badge key={c.id} variant="secondary">
                        {c.name}
                      </Badge>
                    ))}
                  </div>
                )}

                {newColOpen && (
                  <div className="mt-3 grid gap-2 rounded-lg border p-3">
                    <div className="grid gap-1">
                      <Label htmlFor="new-col-name">Name</Label>
                      <Input
                        id="new-col-name"
                        placeholder="e.g. Onboarding Docs"
                        value={newColName}
                        onChange={(e) => setNewColName(e.target.value)}
                      />
                    </div>
                    <div className="grid gap-1">
                      <Label htmlFor="new-col-desc">Description</Label>
                      <Input
                        id="new-col-desc"
                        placeholder="Optional description"
                        value={newColDesc}
                        onChange={(e) => setNewColDesc(e.target.value)}
                      />
                    </div>
                    <label className="inline-flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={newColPublic}
                        onChange={(e) => setNewColPublic(e.target.checked)}
                      />
                      Public (shareable)
                    </label>
                    <div className="flex gap-2">
                      <Button type="button" size="sm" onClick={createCollection}>
                        Create
                      </Button>
                      <Button type="button" size="sm" variant="ghost" onClick={() => setNewColOpen(false)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Dropzone */}
              <div
                className={`rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                  isDragging ? "border-primary bg-primary/5" : "border-border"
                }`}
                onDrop={onDrop}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                role="button"
                onClick={() => fileInputRef.current?.click()}
              >
                <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
                <p className="mt-2 text-sm font-medium">Drag & drop files here</p>
                <p className="text-xs text-muted-foreground">or click to browse</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={onPickFiles}
                  className="mt-4 hidden"
                  accept=".pdf,.txt,.docx,.md"
                />
              </div>

              {/* Staged files */}
              {files.length > 0 && (
                <div className="space-y-3">
                  <Label className="text-sm font-medium">Staged Files ({files.length})</Label>
                  <div className="space-y-2">
                    {files.map((f, idx) => (
                      <div key={idx} className="grid gap-3 rounded-lg border p-3 md:grid-cols-[1fr,1fr,140px]">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <div className="min-w-0">
                            <div className="truncate text-sm font-medium">{f.file.name}</div>
                            <div className="text-xs text-muted-foreground">{(f.file.size / 1024).toFixed(1)} KB</div>
                          </div>
                        </div>
                        <div className="grid gap-2">
                          <Input
                            value={f.title}
                            onChange={(e) =>
                              setFiles((prev) => {
                                const copy = [...prev]
                                copy[idx] = { ...copy[idx], title: e.target.value }
                                return copy
                              })
                            }
                            placeholder="Title"
                          />
                          <Input
                            value={f.description}
                            onChange={(e) =>
                              setFiles((prev) => {
                                const copy = [...prev]
                                copy[idx] = { ...copy[idx], description: e.target.value }
                                return copy
                              })
                            }
                            placeholder="Description (optional)"
                          />
                        </div>
                        <div className="flex items-center justify-end gap-2">
                          {f.status === "uploading" && (
                            <div className="w-full">
                              <div className="flex items-center justify-between text-xs text-muted-foreground">
                                <span>Uploading…</span>
                                <span>{f.progress}%</span>
                              </div>
                              <Progress value={f.progress} className="mt-1" />
                            </div>
                          )}
                          {f.status === "processing" && (
                            <div className="flex items-center gap-2 text-xs text-amber-600">
                              <Loader2 className="h-4 w-4 animate-spin" /> Processing
                            </div>
                          )}
                          {f.status === "done" && (
                            <div className="flex items-center gap-1 text-xs text-green-600">
                              <CheckCircle2 className="h-4 w-4" /> Uploaded
                            </div>
                          )}
                          {f.status === "error" && (
                            <div className="flex items-center gap-1 text-xs text-red-600">
                              <AlertTriangle className="h-4 w-4" /> {f.error || "Error"}
                            </div>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="ml-2"
                            onClick={() => removeFile(idx)}
                            disabled={f.status === "uploading"}
                            title="Remove"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>

                  <Button className="w-full" onClick={uploadAll} disabled={uploading}>
                    {uploading ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" /> Uploading…
                      </span>
                    ) : (
                      "Upload & Process"
                    )}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* ===== Ongoing Calls (unchanged) ===== */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Ongoing Calls
              </CardTitle>
              <CardDescription>Real-time monitoring of active conversations</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {ongoingCalls.map((call) => (
                  <div
                    key={call.id}
                    className="flex cursor-pointer items-center justify-between rounded-lg border border-border p-4 transition-colors hover:bg-accent"
                    onClick={() => router.push("/transcripts")}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                        <Phone className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{call.customer}</p>
                        <p className="text-xs text-muted-foreground">Duration: {call.duration}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          call.sentiment === "positive"
                            ? "default"
                            : call.sentiment === "neutral"
                            ? "secondary"
                            : "destructive"
                        }
                      >
                        {call.sentiment}
                      </Badge>
                      <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                    </div>
                  </div>
                ))}
              </div>

              <Button variant="outline" className="mt-4 w-full bg-transparent" onClick={() => router.push("/transcripts")}>
                View All Calls
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* ===== Documents table ===== */}
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>My Knowledge Documents</CardTitle>
              <CardDescription>Uploaded files and processing status</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={refreshDocuments} title="Refresh">
              <RefreshCw className={`h-4 w-4 ${loadingDocs ? "animate-spin" : ""}`} />
            </Button>
          </CardHeader>
          <CardContent>
            {loadingDocs ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </div>
            ) : documents.length === 0 ? (
              <p className="text-sm text-muted-foreground">No documents yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="py-2 pr-4">Title</th>
                      <th className="py-2 pr-4">File</th>
                      <th className="py-2 pr-4">Status</th>
                      <th className="py-2 pr-4">Collections</th>
                      <th className="py-2 pr-0 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((doc) => (
                      <tr key={doc.id} className="border-b last:border-0">
                        <td className="py-3 pr-4">
                          <div className="font-medium">{doc.title || doc.file_name || "Untitled"}</div>
                          {doc.created_at && (
                            <div className="text-xs text-muted-foreground">{new Date(doc.created_at).toLocaleString()}</div>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          {doc.file_url ? (
                            <Link href={doc.file_url} className="text-primary underline" target="_blank">
                              {doc.file_name || "Open"}
                            </Link>
                          ) : (
                            <span className="text-muted-foreground">{doc.file_name || "—"}</span>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          {(() => {
                            const s = (doc.status || "").toLowerCase()
                            if (s === "ready") return <Badge className="bg-green-600 hover:bg-green-600">ready</Badge>
                            if (s === "processing")
                              return (
                                <Badge variant="secondary" className="gap-1">
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> processing
                                </Badge>
                              )
                            if (s === "failed")
                              return (
                                <Badge variant="destructive" className="gap-1">
                                  <AlertTriangle className="h-3.5 w-3.5" /> failed
                                </Badge>
                              )
                            return <Badge variant="outline">{doc.status}</Badge>
                          })()}
                        </td>
                        <td className="py-3 pr-4">
                          <div className="flex flex-wrap gap-1">
                            {(doc.collections || []).map((c) => (
                              <Badge key={c.id} variant="secondary">
                                {c.name}
                              </Badge>
                            ))}
                          </div>
                        </td>
                        <td className="py-3 pr-0">
                          <div className="flex items-center justify-end gap-2">
                            {doc.file_url && (
                              <Button asChild size="sm" variant="outline">
                                <Link href={doc.file_url} target="_blank">
                                  View
                                </Link>
                              </Button>
                            )}
                            <Button size="icon" variant="ghost" onClick={() => deleteDocument(doc.id)} title="Delete">
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
