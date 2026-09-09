import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiPatch, apiPost } from "@/lib/api";
import type { Store } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  store: Store | null;
}

export default function StoreFormDialog({ open, onOpenChange, store }: Props) {
  const qc = useQueryClient();
  const [nome, setNome] = useState("");
  const [token, setToken] = useState("");
  const [demo, setDemo] = useState(true);
  const [prompt, setPrompt] = useState("");

  useEffect(() => {
    if (!open) return;
    setNome(store?.nome ?? "");
    setToken(store?.token ?? "");
    setDemo(store?.demo ?? true);
    setPrompt(store?.bot_prompt ?? "");
  }, [open, store]);

  const save = useMutation({
    mutationFn: async () => {
      const body = { nome, token, demo, bot_prompt: prompt };
      return store
        ? apiPatch<Store>(`/stores/${store.id}`, body)
        : apiPost<Store>("/stores", body);
    },
    onSuccess: (saved) => {
      qc.invalidateQueries({ queryKey: ["stores"] });
      qc.invalidateQueries({ queryKey: ["store", saved.id] });
      toast.success(store ? "Loja atualizada" : "Loja cadastrada", { description: saved.conexao_msg });
      onOpenChange(false);
    },
    onError: () => toast.error("Não foi possível salvar a loja"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg" data-testid="store-form-dialog">
        <DialogHeader>
          <DialogTitle>{store ? "Editar loja" : "Nova loja"}</DialogTitle>
          <DialogDescription>
            Cada token da LAD pertence a uma única loja. Sem token, a loja roda em modo demonstração.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="store-nome">Nome da loja</Label>
            <Input
              id="store-nome"
              data-testid="store-form-nome-input"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Du Cheff Burguer"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="store-token">Token LAD</Label>
            <Input
              id="store-token"
              data-testid="store-form-token-input"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Bearer token fornecido pela LAD Sistemas"
              className="font-mono text-xs"
            />
          </div>
          <label
            className="flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-secondary/40 p-3"
            data-testid="store-form-demo-label"
          >
            <Checkbox
              checked={demo}
              onCheckedChange={(v) => setDemo(Boolean(v))}
              data-testid="store-form-demo-checkbox"
            />
            <span className="text-sm">
              Modo demonstração
              <span className="block text-xs text-muted-foreground">
                Usa um cardápio fictício e cria pedidos simulados — ideal para demonstrar a revenda.
              </span>
            </span>
          </label>
          <div className="grid gap-2">
            <Label htmlFor="store-prompt">Instruções extras do bot</Label>
            <Textarea
              id="store-prompt"
              data-testid="store-form-prompt-input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              placeholder="Ex.: sempre ofereça bebida antes de fechar o pedido."
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} data-testid="store-form-cancel-button">
            Cancelar
          </Button>
          <Button
            onClick={() => save.mutate()}
            disabled={!nome.trim() || save.isPending}
            data-testid="store-form-submit-button"
          >
            {save.isPending ? "Salvando..." : "Salvar loja"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
