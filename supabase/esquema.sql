-- Busca-apto. Favoritos, notas e descartes compartilhados do Erick e da Amanda.
-- Cole tudo no SQL Editor do projeto busca-apto no Supabase e clique em Run.
-- Pode rodar de novo sem problema.

create table if not exists public.membros (
  usuario uuid primary key references auth.users (id) on delete cascade,
  nome text not null
);

create table if not exists public.favoritos (
  id_imovel text not null,
  usuario uuid not null default auth.uid() references auth.users (id) on delete cascade,
  criado_em timestamptz not null default now(),
  primary key (id_imovel, usuario)
);

create table if not exists public.notas (
  id_imovel text primary key,
  texto text not null default '',
  atualizado_em timestamptz not null default now(),
  atualizado_por uuid references auth.users (id) on delete set null
);

create table if not exists public.descartes (
  id_imovel text primary key,
  descartado_por uuid default auth.uid() references auth.users (id) on delete set null,
  criado_em timestamptz not null default now()
);

-- Quem é da casa. Só quem está em membros lê e grava.
create or replace function public.eh_membro()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (select 1 from public.membros where usuario = auth.uid());
$$;

revoke all on function public.eh_membro() from public;
grant execute on function public.eh_membro() to authenticated;

-- Carimba quem editou a nota e quando.
create or replace function public.carimba_nota()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.atualizado_em := now();
  new.atualizado_por := auth.uid();
  return new;
end;
$$;

drop trigger if exists carimba_nota on public.notas;
create trigger carimba_nota
  before insert or update on public.notas
  for each row execute function public.carimba_nota();

grant usage on schema public to authenticated;
grant select on public.membros to authenticated;
grant select, insert, delete on public.favoritos to authenticated;
grant select, insert, update on public.notas to authenticated;
grant select, insert, delete on public.descartes to authenticated;
grant select on public.membros, public.favoritos, public.notas, public.descartes to service_role;

alter table public.membros enable row level security;
alter table public.favoritos enable row level security;
alter table public.notas enable row level security;
alter table public.descartes enable row level security;

drop policy if exists membros_ler on public.membros;
create policy membros_ler on public.membros
  for select to authenticated using (public.eh_membro());

drop policy if exists favoritos_ler on public.favoritos;
create policy favoritos_ler on public.favoritos
  for select to authenticated using (public.eh_membro());
drop policy if exists favoritos_criar on public.favoritos;
create policy favoritos_criar on public.favoritos
  for insert to authenticated with check (public.eh_membro() and usuario = auth.uid());
drop policy if exists favoritos_apagar on public.favoritos;
create policy favoritos_apagar on public.favoritos
  for delete to authenticated using (public.eh_membro() and usuario = auth.uid());

drop policy if exists notas_ler on public.notas;
create policy notas_ler on public.notas
  for select to authenticated using (public.eh_membro());
drop policy if exists notas_criar on public.notas;
create policy notas_criar on public.notas
  for insert to authenticated with check (public.eh_membro());
drop policy if exists notas_editar on public.notas;
create policy notas_editar on public.notas
  for update to authenticated using (public.eh_membro()) with check (public.eh_membro());

drop policy if exists descartes_ler on public.descartes;
create policy descartes_ler on public.descartes
  for select to authenticated using (public.eh_membro());
drop policy if exists descartes_criar on public.descartes;
create policy descartes_criar on public.descartes
  for insert to authenticated with check (public.eh_membro());
drop policy if exists descartes_apagar on public.descartes;
create policy descartes_apagar on public.descartes
  for delete to authenticated using (public.eh_membro());

-- Tempo real. O que um marca aparece na tela do outro.
do $$
begin
  begin alter publication supabase_realtime add table public.favoritos; exception when duplicate_object then null; end;
  begin alter publication supabase_realtime add table public.notas; exception when duplicate_object then null; end;
  begin alter publication supabase_realtime add table public.descartes; exception when duplicate_object then null; end;
end $$;

-- Depois de criar as duas contas em Authentication, rode este trecho
-- trocando os e-mails pelos de vocês.
--
-- insert into public.membros (usuario, nome)
-- select id, 'Erick' from auth.users where email = 'EMAIL_DO_ERICK'
-- on conflict (usuario) do update set nome = excluded.nome;
--
-- insert into public.membros (usuario, nome)
-- select id, 'Amanda' from auth.users where email = 'EMAIL_DA_AMANDA'
-- on conflict (usuario) do update set nome = excluded.nome;
