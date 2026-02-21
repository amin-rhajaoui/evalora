interface TavusPlayerProps {
  conversationUrl: string | null;
  isVisible: boolean;
}

export default function TavusPlayer({ conversationUrl, isVisible }: TavusPlayerProps) {
  if (!isVisible) return null;

  if (!conversationUrl) {
    return (
      <div className="w-full aspect-video rounded-xl overflow-hidden bg-slate-900 flex items-center justify-center">
        <div className="text-center text-slate-400">
          <div className="w-8 h-8 border-2 border-slate-500 border-t-slate-300 rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm font-medium">Connexion avatar...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full aspect-video rounded-xl overflow-hidden">
      <iframe
        src={conversationUrl}
        allow="camera; microphone; autoplay; display-capture"
        className="w-full h-full border-0"
        title="Tavus Avatar"
      />
    </div>
  );
}
