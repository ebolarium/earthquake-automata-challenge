# CH-008: ETAS Üzerine Yenilenme ve Frailty Tabanlı Arka Plan Yeniden Dağıtımı

**Bilimsel değerlendirme dosyası**

**Sürüm:** 1.0

**Tarih:** 30 Ağustos 2026

**Durum:** Retrospektif kanıt tamamlandı; prospektif test henüz başlamadı.

## 1. Yönetici özeti

CH-008, ETAS'ın yerine geçen bağımsız bir deprem oluşum modeli değildir. ETAS'ın
artçı-deprem tetiklenme bileşenini, zaman çekirdeğini, uzamsal çekirdeğini ve
günlük toplam beklenen olay sayısını koruyan bir **ETAS challenger** modelidir.
Getirdiği tek değişiklik, ETAS'ın doğrudan arka plan deprem kütlesinin sınırlı
bir bölümünü hücreler arasında yeniden dağıtmaktır.

Bu yeniden dağıtım iki yalnızca-geçmişe-dayalı gizli durumdan hesaplanır:

1. **Yenilenme yaşı:** Bir hücre veya fay çevresi, ETAS'ın beklediği bağımsız
   deprem etkinliğine kıyasla ne kadar uzun süredir etkili biçimde sıfırlanmadı?
2. **Frailty (kalıcı yerel yatkınlık):** Yakın geçmişte gözlenen bağımsız deprem
   kütlesi, ETAS'ın beklediği kütleden kalıcı ve komşularca desteklenen biçimde
   daha mı yüksek?

Bir depremin bağımsız mı yoksa tetiklenmiş mi olduğu kesin etiketlenmez. ETAS'ın
arka plan posterior olasılığı yumuşak ağırlık olarak kullanılır. Böylece belirgin
artçı kümeleri CH-008'in uzun dönem durumunu otomatik olarak daha az etkiler.

Retrospektif sonuçlar CH-008'in ETAS'a göre pozitif koşullu mekânsal bilgi
kazancı ürettiğini göstermektedir. En güçlü kanıtlar şunlardır:

- Kaliforniya 2019-2022: 5.204 olayda IGPE `+0,005213`;
- Kaliforniya 2023-18 Ağustos 2026: 3.995 olayda IGPE `+0,007865`;
- Yeni Zelanda 2008-2025 dış-coğrafya testi: 2.270 olayda IGPE `+0,018561`.

Bu sonuçlar cesaret vericidir, ancak **ETAS'a prospektif üstünlük iddiası
oluşturmaz**. Modelin değişmeden, tahminler hedef zamanından önce kalıcı olarak
kaydedilerek ve katalog revizyonları yönetilerek en az bir yıl sınanması gerekir.

## 2. Bilimsel soru ve sınırlandırılmış iddia

### 2.1 Soru

ETAS artçı dizilerini güçlü biçimde açıklarken, doğrudan arka plan sismisitesini
çoğunlukla durağan veya yavaş değişen bir bileşen olarak ele alır. ETAS'ın
geçmiş olaylara verdiği arka plan olasılıklarını kullanarak oluşturulan nedensel
yenilenme ve yatkınlık durumu, bir sonraki günün **mekânsal dağılımını** daha iyi
tahmin edebilir mi?

### 2.2 Desteklenen iddia

Mevcut retrospektif deneylerde CH-008, aynı olaylar üzerinde ETAS'tan daha yüksek
olay-konumu koşullu yoğunluğu üretmiştir. Modelin avantajı özellikle ETAS
yoğunluğunun düşük olduğu olaylarda büyümüştür.

### 2.3 Desteklenmeyen iddialar

Mevcut çalışma aşağıdakileri henüz göstermez:

- CH-008'in gelecekte ETAS'ı geçeceğini;
- belirli bir büyük depremin tam zamanını, yerini veya büyüklüğünü bildiğini;
- mutlak gerilme, fay dayanımı veya kırılmaya kalan fiziksel zamanı ölçtüğünü;
- deprem büyüklüğü dağılımını ETAS'tan daha iyi tahmin ettiğini;
- beş istatistiksel olarak bağımsız prospektif deney tamamlandığını.

## 3. ETAS referansı

Kullanılan uzay-zaman ETAS koşullu yoğunluğu genel olarak

```text
lambda_E(t, x) = mu(x) + sum_{i:t_i<t} g(m_i, t-t_i, x-x_i)
```

biçimindedir. `mu` doğrudan arka plan yoğunluğu, `g` ise önceki her depremin
büyüklüğe bağlı üretkenlik, değiştirilmiş Omori zaman azalımı ve büyüklüğe bağlı
uzamsal çekirdekle yaptığı tetiklenme katkısıdır.

Projede kullanılan parametreleştirme, Mizrahi, Nandan ve Wiemer'in uzay-zaman
ETAS uygulamasıyla hizalanmış ve EarthquakeNPP referans çıktıları karşısında
yeniden üretilmiştir. CH-008 değerlendirmesinde ETAS sıradan bir Poisson veya
yalnızca tarihsel yoğunluk haritası değildir; güçlü, akademik uzay-zaman
tetiklenme baz çizgisidir.

## 4. CH-008'in temel fikri

ETAS yoğunluğunu iki parçaya ayıralım:

```text
lambda_E = background + triggering
```

CH-008 yalnızca `background` parçasını değiştirir:

```text
lambda_CH008(t, x) = lambda_E(t, x) + b'_t(x) - b_t(x)
```

Burada `b_t` ETAS arka plan kütlesi, `b'_t` CH-008 tarafından yeniden dağıtılan
arka plan kütlesidir. Şu eşitlik her tahmin gününde korunur:

```text
sum_x b'_t(x) = sum_x b_t(x)
```

Bunun üç sonucu vardır:

- ETAS'ın tetiklenmiş deprem katkısı aynen kalır.
- Günlük toplam oran CH-008 tarafından artırılmaz veya azaltılmaz.
- Kazanç, olayları doğru hücrelere daha fazla; yanlış hücrelere daha az arka
  plan kütlesi ayırmaktan gelir.

Bu nedenle CH-008'in mevcut birincil iddiası **koşullu mekânsal tahmin
iyileşmesidir**.

## 5. Gizli durum 1: büyüklük işaretli yenilenme yaşı

### 5.1 Yumuşak bağımsız-olay ağırlığı

Bir olayın hücre/fay durumunu ne kadar sıfırlayacağı, ETAS'ın olay anındaki
arka plan payıyla ağırlıklandırılır:

```text
p_bg(i) = mu(x_i) / lambda_E(t_i, x_i)
```

Yoğun bir artçı dizisindeki olay için `lambda_E` büyür ve `p_bg` küçülür. Model
bu olayı kesin biçimde "artçı" diye silmez; uzun dönem duruma yaptığı katkıyı
olasılıksal olarak azaltır.

### 5.2 Büyüklük işareti

Her olayın sıfırlama ağırlığı

```text
q(m) = min(1, 10^[gamma_m (m - M_full)])
```

olarak tanımlanır. Küçük olaylar kısmi, yeterince büyük olaylar tam sıfırlama
etkisi taşır. Kilitli değerler `M_full=4,088951` ve `gamma_m=0,358966`'dır.

### 5.3 Yaş güncellemesi

Her hücre veya fay için normalize edilmiş tehlike yaşı `A` şu şekilde ilerler:

```text
A_{t+1} = (A_t + E_t) exp(-O_t)
```

`E_t`, ETAS arka planından ve Gutenberg-Richter altında beklenen büyüklük
işaretinden gelen günlük beklenen sıfırlama tehlikesidir. `O_t`, o gün gözlenen
`p_bg(i) q(m_i)` kütlesidir. Sessizlik yaşı büyütür; bağımsız olma ihtimali ve
büyüklüğü yüksek olaylar yaşı yumuşak biçimde azaltır.

Yerel yaş, komşu düğümlerin yaşıyla `0,676500` oranında harmanlanır. Elde edilen
yaş, birim ortalamalı Brownian Passage Time (BPT) dağılımının hazard fonksiyonuna
verilir. Yalnızca bellek-siz birim hazard'ın üzerindeki pozitif log-hazard
tutulur:

```text
R_t = max(log h_BPT(A_context), 0)
```

Kilitli BPT aperiodisite değeri `0,989282`'dir. Buradaki BPT kullanımı fiziksel
bir fayın bilinen son büyük kırılma tarihini temsil etmez; ETAS tehlike
birimlerinde oluşturulan istatistiksel bir yenilenme saatidir.

## 6. Gizli durum 2: indirimli Gamma-Poisson frailty

Frailty, bir hücre/fay çevresinin ETAS'a göre kalıcı biçimde daha fazla bağımsız
olay üretip üretmediğini ölçer. Beklenen arka plan maruziyeti `X` ve gözlenen
posterior arka plan kütlesi `Y`, geçmişi üstel olarak unutarak güncellenir:

```text
delta = exp[-log(2) / half_life]
X_{t+1} = delta X_t + expected_background_t
Y_{t+1} = delta Y_t + observed_background_mass_t
```

Kilitli yarı ömür `430,582` gündür. Birim ortalamalı Gamma-Poisson önseliyle
posterior log-yatkınlık

```text
F_local = log[(a0 + Y) / (a0 + X)]
```

olarak hesaplanır; `a0=0,673873`'tür. Yerel ve komşu değerler `0,089383`
komşuluk oranıyla harmanlanır. `0,005165` log-eşiğinin altında kalan ve negatif
değerler sıfırlanır. Böylece frailty yalnızca pozitif, kalıcı ve kısmen mekânsal
destekli fazlalığı modele sokar.

Frailty fiziksel fay dayanımının doğrudan tahmini değildir. Katalog ve ETAS
beklentisinden çıkarılan boyutsuz, istatistiksel bir yerel yatkınlık göstergesidir.

## 7. Skorun arka plan kütlesine dönüştürülmesi

Hücre/fay skoru

```text
S_t = 2,926204 R_t + 0,582796 F_t
```

şeklindedir. Kaliforniya uygulamasında fay dallarının skorları grid hücrelerine
yakınlık ağırlıklarıyla taşınır ve en az `0,774396` dal desteği isteyen bir
consensus filtresinden geçirilir.

ETAS arka plan olasılığı `p0(x)=b_t(x)/B_t` olsun. Eğilmiş dağılım

```text
p_tilt(x) proportional_to p0(x) exp[min(S_t(x), 4)]
```

olarak hesaplanır. Son dağılım tam eğim değildir:

```text
p_CH008 = (1-eta) p0 + eta p_tilt
eta = 0,275925
b'_t = B_t p_CH008
```

Dolayısıyla arka plan kütlesinin en az yaklaşık `%72,4`'ü her zaman doğrudan
ETAS dağılımında kalır. Log-eğim de `4` ile sınırlıdır. Bu iki sınır modelin
yanlış bir gizli durum halinde ETAS'tan kontrolsüz biçimde uzaklaşmasını önler.

## 8. Günlük nedensel işlem sırası

Her hedef gün için işlem sırası değişmez:

1. Gün başlamadan önce mevcut ETAS tahmini ve yalnızca önceki günlerden gelen
   CH-008 durumu okunur.
2. Yenilenme ve frailty skorları hesaplanır.
3. ETAS arka plan kütlesi sınırlı ve kütle-koruyan biçimde yeniden dağıtılır.
4. Tahmin kalıcı olarak yayımlanır.
5. Hedef gün bittikten ve katalog kesim zamanı geçtikten sonra o günün olayları
   ETAS posterior arka plan ağırlıklarıyla duruma eklenir.

Tahmin aynı günün olaylarıyla güncellenmeden önce üretilir. Prospektif sistemde
bu sıra zaman damgalı ve değiştirilemez tahmin dosyalarıyla kanıtlanmalıdır.

## 9. Bölgesel ölçek normalizasyonu

Kaliforniya dışına taşımada aynı sayısal yenilenme saatinin doğrudan kullanılması
uygun değildir; hücre alanı, ETAS `mu` değeri, katalog süresi ve aktivite seviyesi
bölgeden bölgeye değişir. Bu nedenle yalnızca eğitim dönemi bilgisiyle tek bir
ölçek hesaplanır:

```text
c_region = 1 / mean_cell(background_mass * pre_evaluation_days)
```

Beklenen günlük yenilenme tehlikesi ve gözlenen işaretli sıfırlama kütlesi aynı
`c_region` ile çarpılır. Böylece değerlendirme başlamadan önce ortalama hücre
yenilenme maruziyeti `1` olur. CH-008'in yedi parametresi değiştirilmez ve hedef
dönemin olayları bu ölçeği belirlemez.

Bu katman CH-008'in **bölgesel adaptörüdür**. Kaliforniya uygulamasındaki
UCERF3 fay geometrisi yerine Japonya ve Yeni Zelanda'da `0,5` derecelik komşu
hücre grafiği kullanılmıştır. Bu nedenle dış-bölge sonuçları aynı mekanizma ve
aynı parametre ailesini sınar, fakat Kaliforniya yürütülebilir dosyasının birebir
aynı geometrik temsili değildir.

## 10. Kilitli parametreler

| Parametre | Değer | İşlev |
| --- | ---: | --- |
| Tam sıfırlama büyüklüğü | 4,088951 | Büyüklük işaretinin doyma noktası |
| Büyüklük üssü | 0,358966 | Kısmi sıfırlamanın büyüklük duyarlılığı |
| BPT aperiodisite | 0,989282 | Yenilenme hazard biçimi |
| Yenilenme komşuluk karışımı | 0,676500 | Yerel/komşu yaş karışımı |
| Frailty önsel maruziyeti | 0,673873 | Gamma-Poisson düzenleme |
| Frailty hafıza yarı ömrü | 430,582 gün | Eski kanıtın unutulması |
| Frailty komşuluk karışımı | 0,089383 | Yerel/komşu frailty karışımı |
| Minimum log-frailty | 0,005165 | Pozitif fazlalık eşiği |
| Frailty ağırlığı | 0,582796 | Birleşik skordaki katkı |
| Yenilenme ağırlığı | 2,926204 | Birleşik skordaki katkı |
| Yeniden dağıtılan azami karışım | 0,275925 | Eğilmiş arka plan payı |
| Azami log-eğim | 4,0 | Hücre eğiminin güvenlik sınırı |

Model seçimi, 2007 başlangıçlı puanlanmayan ısınma sonrasında Kaliforniya
2014-2018 geliştirme döneminde 64 Sobol noktası ve tam kontrol adayı arasından
yapılmıştır. 2019 sonrası sonuçlar parametre seçiminde kullanılmamıştır.

## 11. Başarı metriği

Bir hedef olay `i` için ETAS'a karşı bilgi kazancı

```text
IG_i = log[lambda_CH008(i) / lambda_ETAS(i)]
```

ve olay başına ortalama bilgi kazancı

```text
IGPE = (1/N) sum_i IG_i
```

olarak hesaplanır. `IGPE>0`, gözlenen olaylarda CH-008'in geometrik ortalama
yoğunluğunun ETAS'tan yüksek olduğunu gösterir. Raporlanan göreli faktör
`exp(IGPE)`'dir.

CH-008 günlük toplam oranı koruduğu için iki modelin point-process compensator
farkı ideal sözleşmede sıfırdır; karşılaştırma olay-konumu log-oranlarına iner.
Belirsizlik, sessiz ve kümeli günlerin bağımlılığını kısmen korumak için 10.000
tekrarlı durağan günlük blok bootstrap ile, 30 ve 90 günlük ortalama bloklarda
hesaplanmıştır.

Bu metrikte küçük bir sayı önemsiz olmak zorunda değildir: örneğin `0,005`
IGPE, çok sayıda olay boyunca biriken pozitif log-olasılık farkıdır. Bununla
birlikte bilimsel önem yalnızca nokta tahminine değil, güven aralığına,
zamansal kararlılığa, büyüklük tabakalarına ve prospektif tekrara dayanmalıdır.

## 12. Retrospektif sonuçlar

### 12.1 Ana sonuç tablosu

| Skor alanı | Dönem | Eşik | Olay | IGPE | `exp(IGPE)` | 30 gün alt sınır | 90 gün alt sınır | Kanıt sınıfı |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Kaliforniya | 2019-2022 | M2,5+ | 5.204 | +0,005213 | 1,005227 | +0,001982 | +0,001844 | Tek-kullanımlık geliştirme validasyonu |
| Kaliforniya | 2023-18.08.2026 | M2,5+ | 3.995 | +0,007865 | 1,007896 | +0,005093 | +0,005369 | Kilitli destekleyici retrospektif |
| Japonya A | 1996-2003 | M4,5+ | 128 | +0,010242 | 1,010295 | +0,006743 | +0,006797 | Sonuçtan sonra geliştirilmiş bölgesel adaptör |
| Japonya B | 1996-2003 | M4,5+ | 726 | +0,001134 | 1,001135 | +0,000841 | +0,000792 | Sonuçtan sonra geliştirilmiş bölgesel adaptör |
| Japonya C | 1996-2003 | M5,0+ | 263 | +0,001342 | 1,001343 | +0,000832 | +0,000795 | Sonuçtan sonra geliştirilmiş bölgesel adaptör |
| Yeni Zelanda CSEP | 2008-2025 | M4,0+, derinlik <40 km | 2.270 | +0,018561 | 1,018735 | +0,012006 | +0,011817 | Ön-kayıtlı dış-coğrafya retrospektifi |

### 12.2 Kaliforniya mekanizma ayrıştırması

2019-2022 döneminde tam CH-008'in yenilenme-only sürümüne ek frailty kazancı
`+0,000802` IGPE'dir. 30 ve 90 günlük alt sınırlar sırasıyla `+0,000409` ve
`+0,000401`'dir. 2023-2026 döneminde frailty artışı `+0,001816`, alt sınırlar
`+0,001238` ve `+0,001270` olmuştur. Bu, frailty bileşeninin birleşik modelde
ölçülebilir katkı verdiğine dair destek sağlar.

Kaliforniya 2019-2022'de ETAS yoğunluğu düşük olaylar için IGPE `+0,022916`,
M4+ olaylar için `+0,008580`'dir. Bu sonuç CH-008'in yalnızca sık artçı
kümelerinde kazanmadığı hipoteziyle uyumludur; yine de bu tabakalar bağımsız
prospektif doğrulama değildir.

### 12.3 Yeni Zelanda zamansal kararlılığı

Yeni Zelanda'nın altı üç-yıllık diliminin tamamı pozitiftir: `+0,007946`,
`+0,018169`, `+0,009287`, `+0,029907`, `+0,042641`, `+0,060180`. Son yıllardaki
artış ilgi çekicidir, fakat katalog homojenliği, ağ değişimleri ve olay
büyüklüğü revizyonları incelenmeden fiziksel rejim değişimi olarak
yorumlanmamalıdır.

## 13. Neden ETAS'tan daha iyi olabilir?

Sonuçların model tasarımıyla uyumlu açıklaması şöyledir:

1. ETAS, kısa dönem tetiklenmiş kümelenmede güçlüdür; CH-008 bu gücü bozmaz.
2. ETAS'ın arka plan bileşeninde eksik kalan orta-uzun dönem yerel zaman
   değişkenliği, yenilenme yaşı ve frailty ile temsil edilir.
3. ETAS'ın yumuşak arka plan posterioru, açık ve hataya duyarlı bir declustering
   etiketine gerek bırakmaz.
4. Büyüklük işaretli yumuşak sıfırlama, küçük ve büyük olayların gizli duruma
   aynı etkiyi yapmasını engeller.
5. Komşuluk ve fay-dalı consensus, tek hücrelik gürültünün etkisini azaltır.
6. Kütle koruma, sınırlı karışım ve log-eğim tavanı, yalnızca güçlü sinyal
   görülen yerlerde ETAS'tan ölçülü uzaklaşma sağlar.

Bu açıklama mekanistik olarak makuldür; henüz nedensel jeofizik ispat değildir.
Özellikle `yenilenme yaşı` ve `frailty`, doğrudan ölçülmüş gerilme veya dayanım
değil, ETAS-normalize katalog durumlarıdır.

## 14. Kanıtın güçlü yanları

- Akademik uzay-zaman ETAS baz çizgisi kaynak ve sürüm hash'leriyle kilitlidir.
- CH-008 parametreleri 2019 sonrası sonuçlar açılmadan önce kilitlenmiştir.
- Her gün tahmin-önce, gözlem-sonra sıralaması uygulanmıştır.
- ETAS tetiklenmesi ve toplam arka plan kütlesi korunduğundan karşılaştırma
  yorumlanabilir ve kontrollüdür.
- Frailty katkısı renewal-only ablation'a karşı eşleştirilmiş olarak sınanmıştır.
- 30 ve 90 günlük blok bootstrap sonuçları zamansal kümelenmeyi hesaba katmaya
  çalışır.
- Ana Kaliforniya dönemlerinin tüm yılları; Yeni Zelanda'nın tüm üç-yıllık
  dilimleri pozitiftir.
- Yeni Zelanda bölgesi, eşikler ve kabul kapıları olay sayıları açılmadan önce
  kaydedilmiştir.

## 15. Sınırlılıklar ve kuruldan saklanmaması gereken noktalar

1. **Prospektif kanıt yoktur.** Bütün skorlanan dönemler bugün geçmiştedir.
2. **Beş bağımsız bölge yoktur.** Beş bölgesel skor tanımı vardır. Japonya C,
   A ve B alanlarını kapsar; sonuçlar korelasyonludur.
3. **Japonya kanıtı geliştirme niteliğindedir.** Bölgesel normalizasyon Japonya
   sonuçları görüldükten sonra geliştirilmiş ve 1996-2003 döneminde sınanmıştır.
   Normalize model için 2004 sonrası ayrılmış test henüz raporlanmamıştır.
4. **Üç ana coğrafi sistem vardır:** Kaliforniya, Japonya ve Yeni Zelanda.
5. **Geometrik uygulamalar aynı değildir.** Kaliforniya UCERF3 fay ağı ve dal
   consensus'u; Japonya/Yeni Zelanda hücre-komşuluk adaptörünü kullanır.
6. **Hedef eşikleri farklıdır.** Kaliforniya M2,5+, Japonya M4,5/M5+, Yeni
   Zelanda M4+ kullanır. Ham IGPE'ler doğrudan eşdeğer etki büyüklükleri değildir.
7. **Kataloglar sonradan revize olabilir.** Retrospektif son katalog, gerçek
   zamanda mevcut ilk katalogdan daha kaliteli olabilir.
8. **Model büyüklük tahminini değiştirmez.** Mevcut kazanç esas olarak mekânsal
   arka plan tahsisindedir.
9. **Bir yıllık güç sınırlı olabilir.** Japonya A gibi seyrek alanlarda tek yıl
   güvenilir bölge-bazlı üstünlük kararı için az olay üretebilir.
10. **Çoklu karşılaştırma riski vardır.** Beş skorun hepsini bağımsız başarı
    kapısı saymak yanlış-pozitif oranını ve kanıt yorumunu bozar.
11. **Dış bölgelerde ETAS ve adaptör protokolü birleştirilmelidir.** Retrospektif
    bölgesel event-intensity değerlendirmesi ile önceden yayımlanan günlük grid
    tahmini aynı operasyonel sözleşmeye dönüştürülmelidir.

## 16. Prospektif testten önce dondurulması gerekenler

Bilim kurulu değerlendirmesinden sonra, ilk hedef gün başlamadan önce aşağıdaki
konular tek bir sürümlü protokolde kesinleştirilmelidir:

- Her bölgenin kesin maskesi, derinlik ve minimum büyüklük eşiği;
- Japonya için A/B/C'nin rapor rolleri ve bağımsız olmayan C'nin birincil toplam
  karara girip girmeyeceği;
- her bölgede ETAS eğitim dönemi, yeniden-fit sıklığı ve parametre güncelleme
  kuralı;
- CH-008 bölgesel adaptörünün tek ve değişmez sürümü;
- günlük issue saati, hedef pencere ve geç gelen katalog olayları politikası;
- tahmin dosyasının hedef pencereden önce hash'lenmesi ve harici zaman damgası;
- birincil metrik, bölge-bazlı ikincil metrikler ve çoklu test düzeltmesi;
- minimum gün ve olay sayısı; bir yıl sonunda güç yetersizse uzatma kuralı;
- 30/90 günlük blok bootstrap yanında CSEP N-, S- ve karşılaştırmalı testler;
- veri kesintisi, servis gecikmesi, kod hatası ve yeniden çalışma politikası;
- model değişikliğinin CH-008 sonucunu geçersiz kılacağı ve yeni model kimliği
  gerektireceği kuralı;
- sonuç ne olursa olsun eksiksiz yayımlama taahhüdü.

Önerilen birincil karar, örtüşmeyen coğrafi sistemler üzerinde önceden tanımlı
bir birleşik eşleştirilmiş IGPE olmalı; beş skor alanı ayrı ayrı raporlanmalıdır.
Bir yıllık süre sabit olabilir, fakat kesin üstünlük kararı için önceden
belirlenmiş minimum olay sayısı sağlanmazsa test otomatik olarak uzamalıdır.

## 17. Kurulun değerlendirmesine sunulan sorular

1. Arka plan kütlesini koruyan koşullu mekânsal IGPE, birincil iddia için yeterli
   midir; yoksa tam joint space-time-magnitude likelihood zorunlu mudur?
2. Bölgesel normalizasyon fiziksel olarak ve istatistiksel olarak kabul edilebilir
   bir ön-hedef adaptasyon mudur?
3. UCERF3 fay-temsili ile hücre-grafiği temsili aynı model ailesi altında mı,
   yoksa iki ayrı model olarak mı önkayıtlanmalıdır?
4. Japonya A/B/C örtüşmesi altında uygun çoklu test ve birincil bölge seçimi
   nedir?
5. Katalog tamlık büyüklüğü ve gerçek-zaman büyüklük revizyonları nasıl
   yönetilmelidir?
6. Bir yıllık test ve beklenen olay sayıları yeterli istatistiksel güç sağlar mı?
7. ETAS parametreleri yıl boyunca sabit mi kalmalı, yoksa yalnızca önceden
   tanımlı periyodik yeniden-fit'e mi izin verilmelidir?
8. Afet iletişimi açısından bu araştırma tahmini kamuya nasıl sunulmalı ve hangi
   ifadelerden kaçınılmalıdır?

## 18. Yeniden üretilebilirlik ve kilitli artefaktlar

Ana model ve kanıt zinciri SHA-256 ile kilitlenmiştir:

- Model: `models/ch008-boundary-sensitivity-v1.json`
- Fit: `data/manifests/ch008-boundary-sensitivity-v1-fit.json`
- Kaliforniya validasyonu:
  `data/manifests/ch008-distinct-regime-v1-validation.json`
- Kaliforniya retrospektifi:
  `data/manifests/ch008-distinct-regime-v1-retrospective.json`
- Prospektif aday dondurması:
  `data/manifests/ch008-prospective-candidate-v1.json`
- Japonya normalizasyon sonucu:
  `data/manifests/fern-ch008-exposure-normalized-validation-v1.json`
- Yeni Zelanda dış-bölge sonucu:
  `data/manifests/nz-ch008-normalized-external-v1.json`
- Ana yürütme modülleri:
  `src/etas_challenge/frailty_renewal_fit.py`,
  `src/etas_challenge/renewal_quiescence.py`,
  `src/etas_challenge/fault_frailty.py`,
  `src/etas_challenge/residual_emergence.py`

Mevcut `ch008-prospective-candidate-v1` durumu `frozen_pending_activation`'dır.
Bu kayıt prospektif toplamanın başladığını iddia etmez; ilk hedef pencereden önce
ayrı bir aktivasyon manifesti gerekir ve geriye dönük tahmin üretmek yasaktır.

## 19. Kaynaklar

- Ogata, Y. (1988), *Statistical Models for Earthquake Occurrences and Residual
  Analysis for Point Processes*,
  [DOI 10.1080/01621459.1988.10478560](https://doi.org/10.1080/01621459.1988.10478560).
- Mizrahi, L., Nandan, S. ve Wiemer, S. (2021), *Embracing Data Incompleteness
  for Better Earthquake Forecasting*,
  [DOI 10.1029/2021JB022379](https://doi.org/10.1029/2021JB022379).
- Matthews, M. V., Ellsworth, W. L. ve Reasenberg, P. A. (2002), *A Brownian
  Model for Recurrent Earthquakes*,
  [DOI 10.1785/0120010267](https://doi.org/10.1785/0120010267).
- Field, E. H. ve diğerleri (2013), *Uniform California Earthquake Rupture
  Forecast, Version 3 (UCERF3)*,
  [USGS Open-File Report 2013-1165](https://pubs.usgs.gov/of/2013/1165/).
- Rhoades, D. A. ve diğerleri (CSEP karşılaştırmalı değerlendirme çerçevesi),
  [pyCSEP test teorisi ve kaynakları](https://docs.cseptesting.org/getting_started/theory.html).
- Politis, D. N. ve Romano, J. P. (1994), *The Stationary Bootstrap*,
  [DOI 10.1080/01621459.1994.10476870](https://doi.org/10.1080/01621459.1994.10476870).
- Zlydenko ve diğerleri (2023), *A Neural Encoder for Earthquake Rate
  Forecasting* (FERN Japonya bölge protokolü),
  [DOI 10.1038/s41598-023-38033-9](https://doi.org/10.1038/s41598-023-38033-9).
- Rhoades ve diğerleri (2010), New Zealand CSEP Testing Centre,
  [DOI 10.1007/s00024-010-0082-4](https://doi.org/10.1007/s00024-010-0082-4).

## 20. Sonuç

CH-008'in yeniliği ETAS'ı reddetmek değil, onun güçlü tetiklenme modelini
koruyarak arka plan sismisitesine sınırlı ve nedensel bir hafıza eklemektir.
Yenilenme yaşı, bir bölgenin beklenen bağımsız olay tehlikesine göre ne kadar
uzun süredir sıfırlanmadığını; frailty ise gözlenen bağımsız olay kütlesinin
ETAS beklentisine göre kalıcı fazlasını temsil eder. Bu iki sinyal yalnızca
ETAS arka plan kütlesinin `%27,6`'ya kadar olan bölümünü yeniden konumlandırır.

Retrospektif sonuçlar tutarlı biçimde pozitiftir ve Yeni Zelanda testi coğrafi
taşınabilirlik için önemli destek sağlamıştır. Bununla birlikte mevcut doğru
bilimsel ifade şudur: **CH-008, prospektif sınamaya değer, hash-kilitli bir ETAS
challenger'ıdır; ETAS'a prospektif üstünlüğü henüz gösterilmemiştir.**
