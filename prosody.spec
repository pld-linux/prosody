Summary:	Flexible communications server for Jabber/XMPP
Name:		prosody
Version:	0.9.2
Release:	1
Group:		Daemons
URL:		http://prosody.im/
License:    MIT
Source0:	http://prosody.im/downloads/source/%{name}-%{version}.tar.gz
# Source0-md5:	bb91f73be0e19d049f1a57951b52c3a2
Source1:	%{name}.init
Source2:	%{name}.tmpfiles
Source3:	%{name}.service
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)
BuildRequires:	libidn-devel
BuildRequires:	lua51-devel
BuildRequires:	openssl-devel
BuildRequires:	systemd-units
Requires:	lua-dbi
Requires:	lua-expat
Requires:	lua-filesystem
Requires:	lua-sec
Requires(post):	systemd-units
Requires(preun):	systemd-units
Requires(postun):	systemd-units

%description
Prosody is a flexible communications server for Jabber/XMPP written in
Lua. It aims to be easy to use, and light on resources. For developers
it aims to be easy to extend and give a flexible system on which to
rapidly develop added functionality, or prototype new protocols.


%prep
%setup -q
sed -e 's|$(PREFIX)/lib|$(PREFIX)/%{_lib}|' -i Makefile
# fix wrong end of line encoding
sed -i -e 's|\r||g' doc/stanza.txt doc/session.txt doc/roster_format.txt

%build
./configure \
  --with-lua-include=%{_includedir}/lua51 \
  --lua-suffix=51 \
  --prefix=%{_prefix}
%{__make} CFLAGS="$RPM_OPT_FLAGS -fPIC"

%install
rm -rf $RPM_BUILD_ROOT
%{__make} install DESTDIR=$RPM_BUILD_ROOT

#fix perms
chmod -x $RPM_BUILD_ROOT%{_libdir}/%{name}/%{name}.version

#avoid rpmlint unstripped-binary-or-object warnings
chmod 0755 $RPM_BUILD_ROOT%{_libdir}/%{name}/util/*.so

#directories for datadir and pids
install -d $RPM_BUILD_ROOT%{_sharedstatedir}/%{name}
chmod 0755 $RPM_BUILD_ROOT%{_sharedstatedir}/%{name}
install -d $RPM_BUILD_ROOT%{_localstatedir}/run/%{name}

#systemd stuff
install -d $RPM_BUILD_ROOT%{systemdunitdir}
install -p %{SOURCE3} $RPM_BUILD_ROOT%{systemdunitdir}/%{name}.service

#tmpfiles.d stuff
install -d $RPM_BUILD_ROOT%{_sysconfdir}/tmpfiles.d
install -p %{SOURCE2} $RPM_BUILD_ROOT%{_sysconfdir}/tmpfiles.d/%{name}.conf

#install initd script
install -d $RPM_BUILD_ROOT%{_initddir}
install %{SOURCE1} $RPM_BUILD_ROOT%{_initddir}/%{name}


%clean
rm -rf $RPM_BUILD_ROOT


%pre
%{_sbindir}/useradd -d %{_sharedstatedir}/%{name} -r -s /sbin/nologin %{name} 2> /dev/null || :

%preun
if [ $1 = 0 ]; then
    %service prosody stop
    /sbin/chkconfig --del prosody
fi
%systemd_preun prosody.service

%post
/sbin/chkconfig --add prosody
%systemd_post prosody.service
umask 077
if [ ! -f %{sslkey} ] ; then
    %{_bindir}/openssl genrsa 1024 > %{sslkey} 2> /dev/null
    chown root:%{name} %{sslkey}
    chmod 640 %{sslkey}
fi

FQDN=`hostname`
if [ "x${FQDN}" = "x" ]; then
   FQDN=localhost.localdomain
fi

if [ ! -f %{sslcert} ] ; then
cat << EOF | %{_bindir}/openssl req -new -key %{sslkey} \
         -x509 -days 365 -set_serial $RANDOM \
         -out %{sslcert} 2>/dev/null
--
SomeState
SomeCity
SomeOrganization
SomeOrganizationalUnit
${FQDN}
root@${FQDN}
EOF
chmod 644 %{sslcert}
fi


%postun
/bin/systemctl daemon-reload >/dev/null 2>&1 || :
if [ $1 -ge 1 ] ; then
    %service -q prosody reload
    %systemd_service_reload prosody.service
fi


%files
%defattr(644,root,root,755)
%doc AUTHORS COPYING HACKERS README TODO doc/*
%attr(755,root,root) %{_bindir}/%{name}
%attr(755,root,root) %{_bindir}/%{name}ctl
%dir %{_libdir}/%{name}
%{_libdir}/%{name}/*
%dir %{_sysconfdir}/%{name}
%config(noreplace) %attr(640, root, %{name}) %{_sysconfdir}/%{name}/*
%config(noreplace) %{_sysconfdir}/tmpfiles.d/%{name}.conf
%{systemdunitdir}/%{name}.service
%attr(755,root,root) %{_initddir}/%{name}
%{_mandir}/man1/*.1*
%dir %attr(-,prosody,prosody) %{_sharedstatedir}/prosody
%dir %attr(-,prosody,prosody) %{_localstatedir}/run/prosody
