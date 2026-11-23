# Alüminyum Tedarik Stokastik Karar Destek Sistemi

MAT 4902 bitirme projesi için geliştirilmiş Türkçe Streamlit karar destek uygulaması. Uygulama, talep, enflasyon ve teslimat süresi belirsizliklerini tek ortak Monte Carlo senaryosunda değerlendirir; beklenen maliyeti minimize eden sipariş miktarı, VaR/CVaR riski, EOQ karşılaştırması ve teslimat gecikmesi stres analizi sunar.

## Hızlı Başlangıç

Windows PowerShell terminalinde proje klasöründe çalıştırın:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502 --server.runOnSave true
```

Tarayıcı adresi: `http://127.0.0.1:8502`

VS Code içinde ayrıca `Run and Debug` panelinden **Streamlit: app.py** profili kullanılabilir.

## Başkalarıyla Paylaşma

Bu Streamlit uygulamasını herkese açık bir web adresiyle paylaşmanın en uygun yolu Streamlit Community Cloud'dur:

1. Projeyi GitHub'a yükleyin.
2. Streamlit Community Cloud'da GitHub hesabınızla oturum açın.
3. `Create app` ekranında repository olarak bu projeyi, branch olarak `main`'i ve ana dosya olarak `app.py` dosyasını seçin.
4. Deploy düğmesine basın; servis size `https://...streamlit.app` biçiminde bir adres verecektir.
5. Uygulamaya erişmek isteyenler sadece bu adresi açar; Python veya VS Code kurmasına gerek yoktur.

Aynı ağdaki kullanıcılarla paylaşmak için bilgisayarda sunucuyu ağdaki tüm arayüzlere açın:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0 --server.port 8502
```

Bağlanan cihazlar `http://BILGISAYAR-IP-ADRESI:8502` adresini açar. Bu yöntem sadece açık port 8502'e ağdan erişime izin veren ve bilgisayar açık olan paylaşım içindir.

## Nihai Modül Yapısı

- `app.py`: Türkçe etkileşimli arayüz, yönetici KPI'ları, risk grafikleri, stres analizi ve rapor indirme.
- `simulation_engine.py`: Senaryo üretimi, Common Random Numbers, maliyet matrisi, EOQ karşılaştırması, VaR/CVaR.
- `data_loader.py`: ALI=F veri yükleme ve açık biçimde etiketlenmiş yerel fallback seri.
- `test_project.py`: Hesap motoru tekrar üretilebilirlik ve veri kaynağı testleri.
- `test_app.py`: Streamlit uygulamasının başlatma ve temel widget testleri.
- `.streamlit/config.toml`: Tutarlı nihai renk ve panel temasını kalıcı olarak tanımlar.

## Matematiksel Model

$$
TC(Q)=P_0(1+i)D+h\frac{Q}{2}+K\frac{D}{Q}+c_s\max(0,L_D-Q)
$$

$$
Q^*=\arg\min_Q E[TC(Q)]
$$

- $D$: Normal dağılımlı aylık talep.
- $i$: Normal veya Student-t dağılımlı aylık enflasyon şoku.
- $L_D$: Teslimat süresine bağlı talep miktarı; teslimat günü/30 ile aylık talep ölçeklenir.
- $K$: Sipariş başına sabit maliyet.
- $h$: Birim elde tutma maliyeti.
- $c_s$: Birim stoksuzluk cezası.
- $P_0$: Güncel birim alüminyum fiyatı.

Tekrarlanabilirlik için rastgelelik tohumu `42` kullanılır. Stres analizi, aday miktarlar ve ortak uniform örnekleri sabit tutarak yalnızca ortalama teslimat süresini değiştirir.

## Risk Ölçütleri

- **VaR %95:** Optimum siparişin toplam maliyet dağılımının %95 kantili.
- **CVaR %95:** VaR'ın üzerindeki en kötü senaryoların ortalaması.
- **EOQ karşılaştırması:** Klasik EOQ'yı stokastik enflasyon, teslimat ve stoksuzluk etkileriyle elde edilen sonuçla karşılaştırır.

## Veri Kaynakları ve Sınırlar

Yahoo Finance ALI=F verisi edinilebildiğinde aylık kapanış serisi kullanılır. Başarısız erişimde yerel yaklaşık seri devreye girer; bu seri LME veya TÜİK verisi değildir ve resmi piyasa fiyatı yerine geçmez. Nihai akademik raporda bu ayrım açıkça belirtilmelidir.

## Kalite Kontrolleri

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Beklenen sonuç: 7 hesap motoru ve Streamlit testinin geçmesi.
