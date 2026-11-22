// Endereço e chave pública do projeto busca-apto no Supabase.
// A chave aqui é a "publishable" (pública). Ela pode ficar no site porque
// as regras do banco (RLS) só deixam o Erick e a Amanda lerem e gravarem.
// Nunca coloque aqui a chave secreta (secret ou service_role).
// Com os dois campos vazios, o site funciona sem login e guarda tudo só no navegador.
window.APTO_CONFIG = {
  supabaseUrl: '',
  supabaseKey: ''
};
