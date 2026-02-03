import React, { useState, useEffect } from 'react';
import { Phone, MessageCircle, ShoppingCart, Wrench, Hammer, Award, Clock, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { CONTACT_INFO, SERVICES, BRANDS, BENEFITS } from './constants';

const App: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const iconMap: any = {
    ShoppingCart: <ShoppingCart size={32} />,
    Wrench: <Wrench size={32} />,
    Hammer: <Hammer size={32} />,
    Award: <Award className="text-red-600" size={40} />,
    Clock: <Clock className="text-red-600" size={40} />,
    ShieldCheck: <ShieldCheck className="text-red-600" size={40} />,
    CheckCircle2: <CheckCircle2 className="text-red-600" size={40} />,
  };

  return (
    <div className="min-h-screen bg-white text-black selection:bg-red-100 selection:text-red-900 relative">
      {/* Header - Versão Compacta com Logotipo em Texto */}
      <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${isScrolled ? 'bg-black/95 backdrop-blur-md shadow-2xl py-2' : 'bg-transparent py-3 md:py-4'}`}>
        <div className="container mx-auto px-4 flex flex-col md:flex-row justify-center md:justify-between items-center gap-2 md:gap-4">
          {/* Logo Section - Texto Ajustado (Mais compacto) */}
          <div className="flex flex-col items-center md:items-start text-center md:text-left transition-all duration-500">
            <span className={`font-black tracking-tighter leading-none transition-all duration-500 ${
              isScrolled 
              ? 'text-lg md:text-xl text-white' 
              : 'text-xl md:text-2xl text-black'
            }`}>
              TOTAL <span className="text-red-600">AQUECEDORES</span>
            </span>
            <span className={`font-bold uppercase tracking-[0.2em] transition-all duration-500 ${
              isScrolled 
              ? 'text-[6px] md:text-[7px] text-gray-400' 
              : 'text-[9px] md:text-[10px] text-gray-600'
            }`}>
              Especialista em Aquecedores
            </span>
          </div>
          
          {/* Contatos Desktop */}
          <div className="hidden md:flex items-center gap-6">
            <a href={`tel:${CONTACT_INFO.phoneRaw}`} className={`flex items-center gap-2 font-bold transition-colors group ${isScrolled ? 'text-white' : 'text-black'} hover:text-red-600`}>
              <div className={`p-2 rounded-full transition-all ${isScrolled ? 'bg-white/10 group-hover:bg-red-600' : 'bg-red-50 group-hover:bg-red-600 group-hover:text-white'}`}>
                <Phone size={16} />
              </div>
              <span className="text-sm lg:text-base">{CONTACT_INFO.phoneDisplay}</span>
            </a>
            <a href={CONTACT_INFO.whatsappUrl} target="_blank" rel="noopener" className="bg-[#25D366] text-white px-5 py-2 rounded-xl font-black text-sm flex items-center gap-2 hover:bg-[#1eb957] transition-all transform hover:-translate-y-0.5 shadow-lg">
              <MessageCircle size={18} /> WhatsApp
            </a>
          </div>
        </div>
      </header>

      {/* Hero (Bloco 1) - Layout Desktop Monumental com mobile abaixo do texto */}
      <section className="relative pt-24 md:pt-32 lg:pt-48 overflow-hidden bg-white">
        {/* Imagem Desktop (Fundo) */}
        <div className="hidden lg:block absolute inset-0 z-0 pointer-events-none">
          <div className="absolute top-0 right-0 w-1/2 h-full overflow-hidden">
            <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-white to-transparent z-20"></div>
            <img 
              src="https://lh3.googleusercontent.com/d/1BOp8FejzekHmMzOMYoCPcUAvj4Er_M5s" 
              alt="Fundo Total Aquecedores" 
              className="w-full h-full object-cover animate-ken-burns"
            />
          </div>
        </div>

        <div className="container mx-auto px-4 relative z-30">
          <div className="grid lg:grid-cols-12 gap-12 items-center">
            <div className="lg:col-span-7 flex flex-col items-center lg:items-start text-center lg:text-left mb-12 lg:mb-32">
              <div className="inline-flex items-center gap-2 bg-red-100 text-red-700 px-4 py-1.5 rounded-full text-[10px] md:text-xs font-black mb-6 md:mb-8 uppercase tracking-wider">
                <span className="w-2 h-2 bg-red-600 rounded-full animate-pulse"></span>
                Atendimento em São Paulo e Região
              </div>
              
              <h1 className="text-3xl md:text-7xl font-black leading-[1.1] mb-6 md:mb-8 tracking-tight">
                Venda, Instalação <br className="hidden md:block" />
                e Manutenção de <br className="hidden md:block" />
                <span className="text-red-600">Aquecedor</span> <br />
                <span className="text-black text-2xl md:text-5xl font-extrabold mt-4 md:mt-6 block">
                  em <span className="underline decoration-red-600/30 decoration-4 underline-offset-8">São Paulo e Região</span>
                </span>
              </h1>

              <p className="text-lg md:text-3xl text-gray-600 mb-8 md:mb-12 font-semibold leading-relaxed">
                Atendimento rápido • +10 anos de experiência
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
                <a href={CONTACT_INFO.whatsappUrl} target="_blank" rel="noopener" className="bg-[#25D366] text-white px-8 py-5 md:py-6 rounded-2xl font-black text-lg md:text-2xl flex items-center justify-center text-center gap-3 hover:bg-[#1eb957] transition-all transform hover:scale-105 whatsapp-pulse shadow-xl shadow-green-200/50 leading-tight">
                  👉 Fale agora no WhatsApp
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Imagem Mobile (Abaixo do texto) */}
        <div className="lg:hidden relative w-full h-[320px] md:h-[450px] overflow-hidden -mt-4">
          <div className="absolute inset-x-0 top-0 h-20 bg-gradient-to-b from-white to-transparent z-10"></div>
          <img 
            src="https://lh3.googleusercontent.com/d/1BOp8FejzekHmMzOMYoCPcUAvj4Er_M5s" 
            alt="Aquecedor Mobile" 
            className="w-full h-full object-cover object-[center_30%] animate-ken-burns opacity-90"
          />
        </div>
      </section>

      {/* Bloco 2 – Apresentação e autoridade */}
      <section className="py-20 bg-black text-white relative overflow-hidden">
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-16 items-center relative z-10">
            <div className="text-left">
              <h2 className="text-3xl md:text-6xl font-black mb-10 flex items-center gap-4 uppercase tracking-tighter italic">
                <span className="w-8 h-1.5 md:w-12 md:h-2 bg-red-600"></span>
                Total Aquecedores
              </h2>
              
              <div className="space-y-6 md:space-y-8 text-gray-300 text-lg md:text-2xl leading-relaxed font-medium">
                <p>
                  A <span className="text-white font-bold">Total Aquecedores</span> é especializada em venda, instalação e manutenção de aquecedores de água, com mais de <span className="text-white font-bold">10 anos de atuação</span> no mercado e mais de <span className="text-white font-bold">5.000 residências atendidas</span> em São Paulo e região.
                </p>
                <p>
                  Atuamos com atendimento técnico qualificado, orientação clara desde o primeiro contato e soluções completas — seja para situações emergenciais, troca de equipamento ou instalação de um novo sistema.
                </p>
              </div>

              <div className="mt-12 md:mt-16">
                <a href={CONTACT_INFO.whatsappUrl} target="_blank" rel="noopener" className="bg-[#25D366] text-white px-10 py-5 rounded-2xl font-black text-lg flex items-center justify-center md:inline-flex gap-4 hover:bg-[#1eb957] transition-all transform hover:scale-105 shadow-[0_0_40px_rgba(37,211,102,0.3)]">
                  Solicitar atendimento
                </a>
              </div>
            </div>

            {/* Imagem Bloco 2 - Oculta no mobile (hidden), visível no desktop (lg:block) */}
            <div className="mt-12 lg:mt-0 hidden lg:block">
              <div className="rounded-[2rem] lg:rounded-[3rem] overflow-hidden shadow-2xl border-4 border-white/10 relative group">
                <div className="absolute inset-0 bg-red-600/10 group-hover:bg-transparent transition-all duration-500"></div>
                <img 
                  src="https://lh3.googleusercontent.com/d/1UenwrJME9vjszegXjAd3i1JXBmsphsd0" 
                  alt="Equipamentos Total Aquecedores" 
                  className="w-full h-auto object-cover opacity-90 group-hover:opacity-100 transition-all duration-500 group-hover:scale-105"
                />
              </div>
            </div>
          </div>
        </div>
        <div className="absolute -top-20 -right-20 w-80 h-80 bg-red-600/10 rounded-full blur-[100px]"></div>
      </section>

      {/* Bloco 3 – Por que nos escolher */}
      <section className="py-20 bg-white relative">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-black tracking-tight mb-4 uppercase">Por que nos escolher?</h2>
            <div className="w-16 md:w-24 h-2 bg-red-600 mx-auto rounded-full"></div>
          </div>
          <div className="grid md:grid-cols-4 gap-8 md:gap-10">
            {BENEFITS.map((b, i) => (
              <div key={i} className="bg-gray-50/50 p-8 md:p-10 rounded-[2rem] md:rounded-[2.5rem] border border-gray-100 hover:border-red-100 hover:bg-white hover:shadow-2xl transition-all group">
                <div className="mb-6 md:mb-8 flex justify-center transform group-hover:scale-110 group-hover:-rotate-6 transition-all duration-500">
                  <div className="p-4 md:p-5 bg-white rounded-2xl md:rounded-3xl shadow-lg border border-gray-50">
                    {iconMap[b.icon]}
                  </div>
                </div>
                <h3 className="text-lg md:text-xl font-black mb-3 md:mb-4 uppercase text-center tracking-tight">{b.title}</h3>
                <p className="text-gray-500 leading-relaxed text-center font-medium text-sm md:text-base">{b.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bloco 4 – Serviços */}
      <section id="servicos" className="py-20 bg-gray-50 border-y border-gray-100">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl md:text-6xl font-black tracking-tighter uppercase mb-4">Nossos Serviços</h2>
            <p className="text-lg md:text-xl text-gray-500 font-medium">Soluções completas para aquecimento de água com segurança garantida.</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8 md:gap-10 mb-16">
            {SERVICES.map((s, i) => (
              <div key={i} className="bg-white p-10 md:p-12 rounded-[2.5rem] md:rounded-[3rem] shadow-sm hover:shadow-xl transition-all flex flex-col items-center text-center group border border-transparent hover:border-red-50">
                <div className="w-20 h-20 md:w-24 md:h-24 bg-black text-white rounded-2xl md:rounded-[2rem] flex items-center justify-center mb-8 md:mb-10 group-hover:bg-red-600 group-hover:rotate-6 transition-all duration-500 shadow-xl">
                  {iconMap[s.icon]}
                </div>
                <h3 className="text-2xl md:text-3xl font-black mb-4 md:mb-6 uppercase tracking-tight">{s.title}</h3>
                <p className="text-gray-500 text-base md:text-lg leading-relaxed mb-8 md:mb-10 flex-grow font-medium">{s.description}</p>
              </div>
            ))}
          </div>

          <div className="flex justify-center">
            <a href={CONTACT_INFO.whatsappUrl} target="_blank" rel="noopener" className="bg-[#25D366] text-white px-12 py-6 rounded-2xl font-black text-xl hover:bg-[#1eb957] transition-all flex items-center gap-3 shadow-xl hover:scale-105 active:scale-95 transform text-center">
              <MessageCircle size={28} /> FALAR COM UM ESPECIALISTA NO WHATSAPP
            </a>
          </div>
        </div>
      </section>

      {/* Bloco 5 – Marcas atendidas */}
      <section className="py-20 bg-white overflow-hidden">
        <div className="container mx-auto px-4">
          <h2 className="text-xl md:text-2xl font-black text-center mb-12 md:text-16 uppercase tracking-[0.3em] text-gray-400">Marcas Atendidas</h2>
          <div className="flex flex-wrap justify-center gap-3 md:gap-8 mb-20 md:mb-24">
            {BRANDS.map((brand, i) => (
              <div key={i} className="px-6 md:px-10 py-4 md:py-6 border border-gray-200 rounded-xl md:rounded-2xl font-black text-lg md:text-2xl text-gray-800 hover:text-red-600 hover:border-red-600 hover:shadow-lg transition-all cursor-default bg-gray-50/30">
                {brand}
              </div>
            ))}
          </div>
          
          <div className="max-w-5xl mx-auto bg-black p-8 md:p-20 rounded-[2.5rem] md:rounded-[4rem] text-white text-center relative overflow-hidden shadow-2xl group">
            <div className="relative z-10">
              <h3 className="text-2xl md:text-6xl font-black mb-6 md:mb-8 tracking-tighter uppercase">
                Problemas com o <span className="text-red-600">seu aquecedor?</span>
              </h3>
              <p className="text-base md:text-2xl mb-10 md:mb-12 text-gray-400 max-w-2xl mx-auto font-medium">Não fique sem água quente. Nossa equipe está pronta para te atender agora mesmo.</p>
              <a href={CONTACT_INFO.whatsappUrl} target="_blank" rel="noopener" className="bg-[#25D366] text-white px-6 md:px-14 py-4 md:py-6 rounded-2xl font-black text-sm md:text-2xl hover:bg-[#1eb957] transition-all inline-flex items-center gap-2 md:gap-3 shadow-[0_0_50px_rgba(37,211,102,0.2)] hover:scale-105 active:scale-95 text-center">
                <MessageCircle size={22} className="md:w-7 md:h-7" /> SOLICITAR ATENDIMENTO AGORA
              </a>
            </div>
            <div className="absolute -top-20 -right-20 w-80 h-80 bg-red-600/10 rounded-full blur-[80px]"></div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white text-black pt-20 pb-40 md:pb-16 border-t border-gray-100">
        <div className="container mx-auto px-4 text-center md:text-left">
          <div className="grid md:grid-cols-3 gap-12 md:gap-16 mb-16">
            <div>
              <span className="font-extrabold text-2xl md:text-3xl block mb-6 md:mb-8 tracking-tighter">TOTAL <span className="text-red-600">AQUECEDORES</span></span>
              <p className="text-gray-500 leading-relaxed max-w-xs mx-auto md:mx-0 font-medium italic text-sm md:text-base">Referência em aquecimento a gás em São Paulo. Qualidade que você sente na pele.</p>
            </div>
            <div>
              <h4 className="font-black text-xs uppercase tracking-[0.2em] text-red-600 mb-6 md:mb-8">Regiões Atendidas</h4>
              <ul className="text-gray-900 space-y-3 md:space-y-4 font-bold grid grid-cols-2 gap-2 text-sm md:text-base">
                <li className="flex items-center gap-2 justify-center md:justify-start"><div className="w-1.5 h-1.5 bg-red-600 rounded-full"></div> SP Capital</li>
                <li className="flex items-center gap-2 justify-center md:justify-start"><div className="w-1.5 h-1.5 bg-red-600 rounded-full"></div> Alphaville</li>
                <li className="flex items-center gap-2 justify-center md:justify-start"><div className="w-1.5 h-1.5 bg-red-600 rounded-full"></div> ABCD</li>
                <li className="flex items-center gap-2 justify-center md:justify-start"><div className="w-1.5 h-1.5 bg-red-600 rounded-full"></div> Barueri</li>
              </ul>
            </div>
            <div>
              <h4 className="font-black text-xs uppercase tracking-[0.2em] text-red-600 mb-6 md:mb-8">Contato Direto</h4>
              <div className="space-y-6">
                <a href={`tel:${CONTACT_INFO.phoneRaw}`} className="flex items-center justify-center md:justify-start gap-3 text-xl md:text-2xl font-black hover:text-red-600 transition-colors group">
                  <div className="p-2.5 bg-red-50 rounded-xl group-hover:bg-red-600 group-hover:text-white transition-all">
                    <Phone size={20} />
                  </div>
                  {CONTACT_INFO.phoneDisplay}
                </a>
              </div>
            </div>
          </div>
          <div className="pt-8 border-t border-gray-100 flex flex-col md:flex-row justify-between items-center gap-4">
             <p className="text-gray-400 text-[10px] md:text-sm font-bold uppercase tracking-wider">© {new Date().getFullYear()} TOTAL AQUECEDORES. TODOS OS DIREITOS RESERVADOS.</p>
          </div>
        </div>
      </footer>

      {/* --- ELEMENTOS FLUTUANTES --- */}
      
      <a 
        href={CONTACT_INFO.whatsappUrl} 
        target="_blank" 
        rel="noopener" 
        className="fixed bottom-24 right-5 md:bottom-10 md:right-10 z-[1000] bg-[#25D366] text-white w-14 h-14 md:w-20 md:h-20 rounded-full flex items-center justify-center shadow-2xl hover:bg-[#1eb957] transition-all transform hover:scale-110 active:scale-90 whatsapp-pulse"
        aria-label="Falar no WhatsApp"
      >
        <MessageCircle size={30} className="md:w-10 md:h-10" />
        <span className="absolute -top-1 -right-1 bg-red-600 text-white text-[9px] font-black px-1.5 py-0.5 rounded-full border-2 border-white animate-bounce">1</span>
      </a>

      <div className="md:hidden fixed bottom-0 left-0 right-0 z-[998] bg-white/95 backdrop-blur-3xl border-t border-gray-100 px-4 py-3 flex gap-3 shadow-[0_-10px_40px_rgba(0,0,0,0.1)] items-center">
        <a href={`tel:${CONTACT_INFO.phoneRaw}`} className="flex-[0.35] bg-black text-white h-11 rounded-xl flex items-center justify-center gap-2 font-black text-[10px] uppercase tracking-widest active:scale-95 transition-all">
          <Phone size={14} /> LIGAR
        </a>
        <a href={CONTACT_INFO.whatsappUrl} target="_blank" rel="noopener" className="flex-1 bg-[#25D366] text-white h-11 rounded-xl flex items-center justify-center gap-2 font-black text-[10px] uppercase tracking-widest active:scale-95 transition-all shadow-lg">
          <MessageCircle size={14} /> WHATSAPP
        </a>
      </div>
    </div>
  );
};

export default App;