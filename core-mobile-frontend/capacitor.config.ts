import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.royalzeni.core',
  appName: 'RZC Mobile',
  webDir: 'dist',
  plugins: {
    GoogleAuth: {
      clientId: '2237565466-rbeblh0n3oah3stpt2266ifdngt5k1po.apps.googleusercontent.com',
      scopes: ['profile', 'email'],
      grantOfflineAccess: true
    }
  }
};

export default config;