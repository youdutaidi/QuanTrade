import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL('https://q-forge-ah-lab.tender-badge-3009.chatgpt.site'),
  title: 'Q-Forge｜A/H 股量化研究台',
  description: '以证据门槛约束收益目标的 A 股与港股因子、策略和模拟回测研究平台。',
  openGraph: {
    title: 'Q-Forge｜先证明它不是幻觉，再追求翻倍',
    description: 'A/H 股因子、策略、模拟回测与风险审计研究台。',
    images: [{ url: '/og.png', width: 1731, height: 909, alt: 'Q-Forge A/H 股量化研究台' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Q-Forge｜先证明它不是幻觉，再追求翻倍',
    description: 'A/H 股因子、策略、模拟回测与风险审计研究台。',
    images: ['/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
